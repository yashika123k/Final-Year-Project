import numpy as np
from sklearn.cluster import KMeans

from node import Node
from simulator import Simulator
from utils import (
    reset_node_for_new_round,
    calculate_transmit_energy,
    calculate_receive_energy,
    calculate_aggregation_energy,
)
from config import (
    DATA_PACKET_SIZE_BITS,
    INITIAL_NODE_ENERGY_J,
    FS_MULTIPATH_THRESHOLD_DISTANCE_M,
)

EPS = 1e-12


class Zcr:

    def __init__(self, cluster_head_probability: float):
        self.cluster_head_probability = cluster_head_probability
        self.near_chs = []
        self.far_chs = []
        self.current_radius = FS_MULTIPATH_THRESHOLD_DISTANCE_M * 1.5

        # FIX A: Track which near CHs are acting as relays this round so we
        # don't double-charge them in the near-CH energy loop. Key = near_ch_id,
        # value = True if it already paid BS-tx cost as a relay this round.
        self._relay_paid_bs_tx: set = set()

    def name(self):
        return "ZCR_ROTATION_V2"

    # =======================
    # DYNAMIC RADIUS
    # =======================
    def _compute_dynamic_radius(self, nodes):
        near_energy, far_energy = [], []

        for n in nodes:
            if not n.is_alive:
                continue
            if n.distance_to_base_station_m <= self.current_radius:
                near_energy.append(n.remaining_energy_j)
            else:
                far_energy.append(n.remaining_energy_j)

        if not near_energy or not far_energy:
            return self.current_radius

        avg_near = sum(near_energy) / len(near_energy)
        avg_far = sum(far_energy) / len(far_energy)

        ratio = avg_near / (avg_far + EPS)

        # Tighter alpha clamp prevents radius swinging too aggressively.
        alpha = np.clip(ratio ** 0.4, 0.85, 1.3)
        new_radius = FS_MULTIPATH_THRESHOLD_DISTANCE_M * alpha * 1.5

        self.current_radius = 0.9 * self.current_radius + 0.1 * new_radius
        return self.current_radius

    # =======================
    # ZONE SPLIT
    # =======================
    def _split_zones(self, nodes):
        radius = self._compute_dynamic_radius(nodes)

        near_ids, far_ids = [], []

        for n in nodes:
            if not n.is_alive:
                continue
            if n.distance_to_base_station_m <= radius:
                near_ids.append(n.id)
            else:
                far_ids.append(n.id)

        return near_ids, far_ids

    # =======================
    # CH SELECTION (ROTATION)
    # =======================
    def _select_chs(self, node_ids, nodes, k, current_round):
        """
        Select k cluster heads from node_ids using KMeans spatial clustering
        combined with an energy/rotation score.

        FIX B: Nodes with very low energy are excluded from CH candidacy.
        This prevents near-dead far nodes from becoming CHs and dying
        immediately, which would leave their cluster members stranded.

        FIX C: k is clamped to the number of *viable* candidates (not just
        alive nodes) so KMeans never gets k > n_samples.
        """
        if len(node_ids) == 0:
            return [], np.array([])

        # Only consider nodes with enough energy to serve as CH
        avg_energy = np.mean([nodes[i].remaining_energy_j for i in node_ids])
        min_ch_energy = avg_energy * 0.25  # must have at least 25% of avg energy

        viable = [i for i in node_ids if nodes[i].remaining_energy_j >= min_ch_energy]
        if not viable:
            viable = node_ids  # fallback: everyone is eligible

        k = min(k, len(viable))  # FIX C
        positions = np.array([nodes[i].position for i in node_ids])

        # Run KMeans on ALL nodes in zone for correct cluster geometry
        k_fit = min(k, len(node_ids))
        kmeans = KMeans(n_clusters=k_fit, n_init=3, random_state=42).fit(positions)
        labels = kmeans.labels_
        centroids = kmeans.cluster_centers_

        selected = [None] * k_fit
        best_scores = [-1e9] * k_fit

        viable_set = set(viable)

        for idx, nid in enumerate(node_ids):
            node = nodes[nid]
            c = labels[idx]

            # FIX B: skip ineligible candidates for CH role
            if nid not in viable_set:
                continue

            # Normalised energy fraction (higher = better)
            energy = node.remaining_energy_j / (INITIAL_NODE_ENERGY_J + EPS)

            # Distance to BS: far CHs are expensive — penalise more
            d_bs = node.distance_to_base_station_m / 500.0

            # Distance to cluster centroid: closer = better relay point
            d_cent = np.linalg.norm(node.position - centroids[c]) / 500.0

            # Cooldown: nodes that were recently CH get suppressed
            rounds_since_ch = current_round - getattr(node, "last_ch_round", -1000)
            cooldown = 1.0 - np.exp(-rounds_since_ch / 5.0)

            # FIX D: Increase energy weight and reduce BS-distance penalty for
            # far zone. We pass this as a unified scorer; callers set the same
            # k multiplier for both zones (symmetry), so no zone-specific
            # weighting is needed here — energy dominance is enough.
            score = (0.75 * energy - 0.05 * d_bs - 0.20 * d_cent) * cooldown

            if score > best_scores[c]:
                best_scores[c] = score
                selected[c] = nid

        # Fallback: fill any unassigned cluster with the first viable node
        for i in range(k_fit):
            if selected[i] is None:
                for nid in node_ids:
                    if nid in viable_set:
                        selected[i] = nid
                        break
                if selected[i] is None:
                    selected[i] = node_ids[0]

        return selected, labels

    # =======================
    # ASSIGN NODES
    # =======================
    def _assign_nodes(self, node_ids, ch_ids, labels, nodes, current_round):
        """
        Assign each non-CH node to its cluster head and charge member TX energy.

        FIX E: Skip nodes that are already dead. Previously dead nodes still
        paid TX energy, which caused remaining_energy to go deeply negative
        and corrupted subsequent comparisons.

        FIX F: Only charge TX energy if the node has enough left; otherwise
        mark it dead immediately. This prevents phantom nodes that appear
        alive but have negative energy.
        """
        ch_set = set(ch_ids)

        for idx, nid in enumerate(node_ids):
            node = nodes[nid]

            # Skip already-dead nodes
            if not node.is_alive:
                continue

            if nid in ch_set:
                node.is_cluster_head = True
                node.taregt_node_id = None
                node.last_ch_round = current_round
                continue

            ch = ch_ids[labels[idx]]
            node.taregt_node_id = ch
            nodes[ch].cluster_member_ids.append(nid)

            d = np.linalg.norm(node.position - nodes[ch].position)
            tx_cost = calculate_transmit_energy(DATA_PACKET_SIZE_BITS, d)

            # FIX F: deduct and check
            node.remaining_energy_j -= tx_cost
            if node.remaining_energy_j <= EPS:
                node.is_alive = False

    # =======================
    # ENERGY HANDLING
    # =======================
    def _handle_ch_energy(self, nodes):
        """
        Charge cluster-head aggregation, receive, and transmission energy.

        Key bug fixes vs. original:
        ─────────────────────────────────────────────────────────────────────
        FIX G  Near CHs that act as relay for a far CH are tracked in
               self._relay_paid_bs_tx so they are NOT double-charged for the
               BS-tx leg in the near-CH loop below.

        FIX H  The near-CH member-aggregation loop runs AFTER the far-CH
               relay loop, and explicitly skips the extra BS-tx cost for
               nodes already charged in FIX G. This eliminates the double-
               charge that was draining near nodes 2× faster than intended.

        FIX I  Dead nodes are skipped at every step so energy doesn't go
               further negative, which kept simulator alive-count wrong.
        ─────────────────────────────────────────────────────────────────────
        """
        self._relay_paid_bs_tx = set()  # reset relay tracker each round

        # ── FAR CHs ──────────────────────────────────────────────────────
        for fid in self.far_chs:
            node = nodes[fid]

            if not node.is_alive:  # FIX I
                continue

            members = len(node.cluster_member_ids)

            # Charge receive + aggregate for every member packet
            node.remaining_energy_j -= members * (
                calculate_receive_energy(DATA_PACKET_SIZE_BITS)
                + calculate_aggregation_energy(DATA_PACKET_SIZE_BITS)
            )

            # ── Find best near-CH relay (must be strictly closer to BS) ──
            best_near = None
            best_dist = float("inf")

            for nid in self.near_chs:
                near = nodes[nid]
                if not near.is_alive:  # FIX I
                    continue
                if near.distance_to_base_station_m >= node.distance_to_base_station_m:
                    continue

                d = np.linalg.norm(node.position - near.position)
                if d < best_dist:
                    best_dist = d
                    best_near = nid

            direct_cost = calculate_transmit_energy(
                DATA_PACKET_SIZE_BITS,
                node.distance_to_base_station_m
            )

            relay_cost = float("inf")
            if best_near is not None:
                # Far CH only pays hop1 (its own transmission to near CH)
                relay_cost = calculate_transmit_energy(DATA_PACKET_SIZE_BITS, best_dist)

            # Relay is chosen only when clearly cheaper (0.9× threshold)
            if best_near is not None and relay_cost < direct_cost * 0.9:
                node.taregt_node_id = best_near
                node.remaining_energy_j -= relay_cost

                near_node = nodes[best_near]

                # Near CH pays: receive + re-aggregate + BS transmission
                near_bs_tx = calculate_transmit_energy(
                    DATA_PACKET_SIZE_BITS,
                    near_node.distance_to_base_station_m
                )
                near_node.remaining_energy_j -= (
                    calculate_receive_energy(DATA_PACKET_SIZE_BITS)
                    + calculate_aggregation_energy(DATA_PACKET_SIZE_BITS)
                    + near_bs_tx
                )

                # FIX G: Mark this near CH as having already paid BS-tx cost
                # so the near-CH loop below does NOT charge it again.
                self._relay_paid_bs_tx.add(best_near)

            else:
                # Direct transmission — far CH sends straight to BS
                node.taregt_node_id = None
                node.remaining_energy_j -= direct_cost

            # FIX I: mark dead after charging
            if node.remaining_energy_j <= EPS:
                node.is_alive = False

        # ── NEAR CHs ─────────────────────────────────────────────────────
        for nid in self.near_chs:
            node = nodes[nid]

            if not node.is_alive:  # FIX I
                continue

            members = len(node.cluster_member_ids)

            # Charge receive + aggregate for own cluster members
            node.remaining_energy_j -= members * (
                calculate_receive_energy(DATA_PACKET_SIZE_BITS)
                + calculate_aggregation_energy(DATA_PACKET_SIZE_BITS)
            )

            node.taregt_node_id = None

            # FIX H: Only charge BS-tx once. If this node was a relay in the
            # far-CH loop above it already paid BS-tx cost there — skip it.
            if nid not in self._relay_paid_bs_tx:
                node.remaining_energy_j -= calculate_transmit_energy(
                    DATA_PACKET_SIZE_BITS,
                    node.distance_to_base_station_m
                )

            # FIX I: mark dead after charging
            if node.remaining_energy_j <= EPS:
                node.is_alive = False

    # =======================
    # MAIN LOOP
    # =======================
    def run_round(self, simulator: Simulator):
        """
        Execute one simulation round:
          1. Reset per-round node state.
          2. Split nodes into near/far zones (dynamic radius).
          3. Select CHs using energy-aware rotation scoring.
          4. Assign members and charge TX energy.
          5. Charge CH aggregation + transmission energy.
          6. Update simulator alive count.

        FIX J: Alive count is recomputed from scratch after all energy
        deductions rather than being decremented ad-hoc, preventing
        accumulated counting errors that caused the simulator to report
        wrong network lifetime.
        """
        nodes = simulator.nodes

        for n in nodes:
            reset_node_for_new_round(n)

            # Ensure rotation attribute exists
            if not hasattr(n, "last_ch_round"):
                n.last_ch_round = -1000

            # FIX K: reset cluster_member_ids here so stale members from
            # previous rounds don't accumulate (reset_node_for_new_round may
            # not clear this list depending on implementation).
            n.cluster_member_ids = []

            # Kill nodes that have exhausted energy
            if n.is_alive and n.remaining_energy_j <= EPS:
                n.is_alive = False

        near_ids, far_ids = self._split_zones(nodes)

        # Symmetric CH probability multiplier for both zones (FIX #6 preserved)
        k_near = max(1, round(len(near_ids) * self.cluster_head_probability)) if near_ids else 0
        k_far  = max(1, round(len(far_ids)  * self.cluster_head_probability)) if far_ids else 0

        near_chs, near_labels = self._select_chs(
            near_ids, nodes, k_near, simulator.current_round
        )
        far_chs, far_labels = self._select_chs(
            far_ids, nodes, k_far, simulator.current_round
        )

        self.near_chs = near_chs
        self.far_chs = far_chs

        self._assign_nodes(near_ids, near_chs, near_labels, nodes, simulator.current_round)
        self._assign_nodes(far_ids, far_chs, far_labels, nodes, simulator.current_round)

        self._handle_ch_energy(nodes)

        # FIX J: recount alive nodes from ground truth after all deductions
        simulator.alive_node_count = sum(1 for n in nodes if n.is_alive)
