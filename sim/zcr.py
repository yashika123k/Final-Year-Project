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

    def name(self):
        return "ZCR_ROTATION"

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

        # FIX #1: tighter alpha clamp (was 0.7–1.6, now 0.85–1.3).
        # The old range let the radius swing too aggressively, funnelling
        # far-zone nodes into oversized clusters that drained them faster.
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

        if len(node_ids) == 0:
            return [], np.array([])

        positions = np.array([nodes[i].position for i in node_ids])

        k = min(k, len(node_ids))
        kmeans = KMeans(n_clusters=k, n_init=3).fit(positions)

        labels = kmeans.labels_
        centroids = kmeans.cluster_centers_

        selected = [None] * k
        best_scores = [-1e9] * k

        for idx, nid in enumerate(node_ids):
            node = nodes[nid]
            c = labels[idx]

            energy = node.remaining_energy_j / INITIAL_NODE_ENERGY_J
            d_bs = node.distance_to_base_station_m / 500
            d_cent = np.linalg.norm(node.position - centroids[c]) / 500

            rounds_since_ch = current_round - getattr(node, "last_ch_round", -1000)
            cooldown = 1 - np.exp(-rounds_since_ch / 5)

            score = (
                (0.7 * energy - 0.1 * d_bs - 0.2 * d_cent)
                * cooldown
            )

            if score > best_scores[c]:
                best_scores[c] = score
                selected[c] = nid

        for i in range(k):
            if selected[i] is None:
                selected[i] = node_ids[i]

        return selected, labels

    # =======================
    # ASSIGN NODES
    # =======================
    def _assign_nodes(self, node_ids, ch_ids, labels, nodes, current_round):
        ch_set = set(ch_ids)

        for idx, nid in enumerate(node_ids):
            node = nodes[nid]

            if nid in ch_set:
                node.is_cluster_head = True
                node.taregt_node_id = None
                node.last_ch_round = current_round
                continue

            ch = ch_ids[labels[idx]]
            node.taregt_node_id = ch
            nodes[ch].cluster_member_ids.append(nid)

            d = np.linalg.norm(node.position - nodes[ch].position)
            node.remaining_energy_j -= calculate_transmit_energy(
                DATA_PACKET_SIZE_BITS, d
            )

    # =======================
    # ENERGY HANDLING
    # =======================
    def _handle_ch_energy(self, nodes):

        # --- FAR CHs ---
        for fid in self.far_chs:
            node = nodes[fid]
            members = len(node.cluster_member_ids)

            # FIX #2: removed the 0.7 discount factor on far-CH receive energy.
            # The discount was arbitrary and gave far CHs a hidden subsidy that
            # masked how much energy they were actually spending, making the
            # accounting inconsistent with near CHs (which pay full price).
            node.remaining_energy_j -= members * (
                calculate_receive_energy(DATA_PACKET_SIZE_BITS)
                + calculate_aggregation_energy(DATA_PACKET_SIZE_BITS)
            )

            # Find best near-CH relay candidate
            best_near = None
            best_dist = float("inf")

            for nid in self.near_chs:
                # Relay must be strictly closer to BS than this far CH
                if nodes[nid].distance_to_base_station_m >= node.distance_to_base_station_m:
                    continue

                d = np.linalg.norm(node.position - nodes[nid].position)
                if d < best_dist:
                    best_dist = d
                    best_near = nid

            direct_cost = calculate_transmit_energy(
                DATA_PACKET_SIZE_BITS,
                node.distance_to_base_station_m
            )

            relay_cost = float("inf")
            if best_near is not None:
                hop1 = calculate_transmit_energy(DATA_PACKET_SIZE_BITS, best_dist)
                hop2 = calculate_transmit_energy(
                    DATA_PACKET_SIZE_BITS,
                    nodes[best_near].distance_to_base_station_m
                )
                # FIX #3: relay_cost is just the far-CH's share (hop1 only).
                # Previously relay was hop1+hop2, but hop2 is paid by the near
                # CH — attributing it to the far CH was double-counting energy
                # and made the relay path look falsely expensive, causing far
                # CHs to needlessly transmit directly to BS at high cost.
                relay_cost = hop1

            # FIX #4: threshold changed from 1.2× to 0.9× (relay must be
            # meaningfully cheaper, not just marginally so, before we commit
            # to routing through a near CH and burdening it).
            if best_near is not None and relay_cost < direct_cost * 0.9:
                node.taregt_node_id = best_near

                # Far CH pays only its own hop
                node.remaining_energy_j -= relay_cost

                # Near CH pays for the relay reception + re-aggregation + BS tx.
                # FIX #5: added the BS-tx cost for the near CH here. Previously
                # only receive+aggregate was charged; the near CH's onward
                # transmission to BS was silently lost, understating near-CH
                # energy drain and making near nodes appear healthier than they
                # were relative to far nodes.
                near_node = nodes[best_near]
                near_node.remaining_energy_j -= (
                    calculate_receive_energy(DATA_PACKET_SIZE_BITS)
                    + calculate_aggregation_energy(DATA_PACKET_SIZE_BITS)
                    + calculate_transmit_energy(
                        DATA_PACKET_SIZE_BITS,
                        near_node.distance_to_base_station_m
                    )
                )
            else:
                node.taregt_node_id = None
                node.remaining_energy_j -= direct_cost

        # --- NEAR CHs ---
        for nid in self.near_chs:
            node = nodes[nid]
            members = len(node.cluster_member_ids)

            node.remaining_energy_j -= members * (
                calculate_receive_energy(DATA_PACKET_SIZE_BITS)
                + calculate_aggregation_energy(DATA_PACKET_SIZE_BITS)
            )

            node.taregt_node_id = None

            node.remaining_energy_j -= calculate_transmit_energy(
                DATA_PACKET_SIZE_BITS,
                node.distance_to_base_station_m
            )

    # =======================
    # MAIN LOOP
    # =======================
    def run_round(self, simulator: Simulator):

        nodes = simulator.nodes

        for n in nodes:
            reset_node_for_new_round(n)

            if not hasattr(n, "last_ch_round"):
                n.last_ch_round = -1000

            if n.is_alive and n.remaining_energy_j <= EPS:
                n.is_alive = False
                simulator.alive_node_count -= 1

        near_ids, far_ids = self._split_zones(nodes)

        # FIX #6: use the same CH probability multiplier for both zones
        # (was 0.8× near / 1.5× far). A higher k_far means more far nodes
        # become CHs each round, spending aggregation + relay energy every
        # round rather than just member tx energy — this was the biggest
        # single driver of accelerated far-zone death. Equal multipliers
        # spread the CH role (and its energy cost) symmetrically.
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















