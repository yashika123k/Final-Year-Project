from __future__ import annotations
import numpy as np
from sklearn.cluster import KMeans

from node import Node
from simulator import Protocol, Simulator
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


class Zcr(Protocol):
    """
    ZCR: Zone-based Cluster Routing (proposed variant).
    - Uses sklearn KMeans to partition nodes into spatial clusters.
    - Selects best CH per cluster by energy + centrality score.
    - Divides CHs into near/far zones; far-zone CHs may relay via nearest near-zone CH.
    """

    def __init__(self, cluster_head_probability: float):
        self.cluster_head_probability = cluster_head_probability
        self.num_cluster_heads: int = 0
        # zone_cluster_heads[0] = far, zone_cluster_heads[1] = near
        self.zone_cluster_heads: list[list[int]] = [[], []]

    def name(self) -> str:
        return "ZCR"

    def _assign_zones(
        self,
        selected_ch_ids: list[int | None],
        nodes: list[Node],
    ) -> None:
        self.zone_cluster_heads = [[], []]
        for ch_id in selected_ch_ids:
            if ch_id is None:
                continue
            dist = nodes[ch_id].distance_to_base_station_m
            if dist <= FS_MULTIPATH_THRESHOLD_DISTANCE_M:
                self.zone_cluster_heads[1].append(ch_id)   # near
            else:
                self.zone_cluster_heads[0].append(ch_id)   # far
            nodes[ch_id].is_cluster_head = True

    def _form_clusters(
        self,
        selected_ch_ids: list[int | None],
        nodes: list[Node],
        cluster_assignments: np.ndarray,
    ) -> None:
        for node_id, cluster_idx in enumerate(cluster_assignments):
            node = nodes[node_id]
            if not node.is_alive or node.is_cluster_head:
                continue
            ch_id = selected_ch_ids[cluster_idx]
            if ch_id is not None:
                node.cluster_head_id = ch_id
                nodes[ch_id].cluster_member_ids.append(node_id)
                dist = float(np.linalg.norm(node.position - nodes[ch_id].position))
                node.remaining_energy_j -= calculate_transmit_energy(DATA_PACKET_SIZE_BITS, dist)

    def _dissipate_ch_energy(self, nodes: list[Node]) -> None:
        # Far-zone CHs
        for far_ch_id in self.zone_cluster_heads[0]:
            min_relay_dist = float("inf")
            best_near_id: int | None = None

            for near_ch_id in self.zone_cluster_heads[1]:
                d = float(np.linalg.norm(nodes[far_ch_id].position - nodes[near_ch_id].position))
                if d < min_relay_dist:
                    min_relay_dist = d
                    best_near_id = near_ch_id

            member_count = len(nodes[far_ch_id].cluster_member_ids)
            nodes[far_ch_id].remaining_energy_j -= (
                calculate_receive_energy(DATA_PACKET_SIZE_BITS)
                + calculate_aggregation_energy(DATA_PACKET_SIZE_BITS)
            ) * member_count

            if best_near_id is not None and min_relay_dist < nodes[far_ch_id].distance_to_base_station_m:
                nodes[far_ch_id].remaining_energy_j -= calculate_transmit_energy(DATA_PACKET_SIZE_BITS, min_relay_dist)
                nodes[best_near_id].remaining_energy_j -= (
                    calculate_receive_energy(DATA_PACKET_SIZE_BITS)
                    + calculate_aggregation_energy(DATA_PACKET_SIZE_BITS)
                )
            else:
                nodes[far_ch_id].remaining_energy_j -= calculate_transmit_energy(
                    DATA_PACKET_SIZE_BITS, nodes[far_ch_id].distance_to_base_station_m
                )

        # Near-zone CHs
        for near_ch_id in self.zone_cluster_heads[1]:
            member_count = len(nodes[near_ch_id].cluster_member_ids)
            nodes[near_ch_id].remaining_energy_j -= member_count * (
                calculate_receive_energy(DATA_PACKET_SIZE_BITS)
                + calculate_aggregation_energy(DATA_PACKET_SIZE_BITS)
            )
            nodes[near_ch_id].remaining_energy_j -= calculate_transmit_energy(
                DATA_PACKET_SIZE_BITS, nodes[near_ch_id].distance_to_base_station_m
            )

    def run_round(self, simulator: Simulator) -> None:
        if simulator.alive_node_count == 0:
            return

        self.num_cluster_heads = max(
            1, int(np.ceil(self.cluster_head_probability * simulator.alive_node_count))
        )

        # Gather alive node positions for KMeans
        alive_ids = [n.id for n in simulator.nodes if n.is_alive]
        positions = np.array([simulator.nodes[i].position for i in alive_ids])

        k = min(self.num_cluster_heads, len(alive_ids))
        kmeans = KMeans(n_clusters=k, n_init=3, max_iter=100)
        kmeans.fit(positions)

        centroids = kmeans.cluster_centers_
        # Map alive node → cluster label
        alive_labels = kmeans.labels_

        # Build full cluster assignment array (dead nodes → cluster 0, won't matter)
        cluster_assignments = np.zeros(len(simulator.nodes), dtype=int)
        for idx, node_id in enumerate(alive_ids):
            cluster_assignments[node_id] = alive_labels[idx]

        # Reset and check death
        for node in simulator.nodes:
            reset_node_for_new_round(node)
            if node.is_alive and node.remaining_energy_j <= 0.0:
                node.is_alive = False
                simulator.alive_node_count -= 1

        # Select best CH per cluster
        selected_ch_ids: list[int | None] = [None] * k
        best_scores: list[float] = [float("-inf")] * k

        DIAG = (500.0 ** 2 + 500.0 ** 2) ** 0.5  # ≈ 707

        for node_id, cluster_idx in enumerate(cluster_assignments):
            node = simulator.nodes[node_id]
            if not node.is_alive:
                continue

            energy_score = node.remaining_energy_j / INITIAL_NODE_ENERGY_J
            centroid = centroids[cluster_idx]
            dist_to_centroid = float(np.linalg.norm(node.position - centroid))
            penalty = dist_to_centroid / DIAG

            score = energy_score - penalty
            if score > best_scores[cluster_idx]:
                best_scores[cluster_idx] = score
                selected_ch_ids[cluster_idx] = node_id

        self._assign_zones(selected_ch_ids, simulator.nodes)
        self._form_clusters(selected_ch_ids, simulator.nodes, cluster_assignments)
        self._dissipate_ch_energy(simulator.nodes)
