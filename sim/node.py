from __future__ import annotations
from typing import Optional
import numpy as np

from config import INITIAL_NODE_ENERGY_J, BASE_STATION_POSITION


class Node:
    def __init__(self, node_id: int, position: np.ndarray):
        self.id = node_id
        self.position = position.astype(np.float32)

        self.remaining_energy_j: float = INITIAL_NODE_ENERGY_J
        self.is_alive: bool = True
        self.is_cluster_head: bool = False
        self.is_eligible_for_ch: bool = True

        self.distance_to_base_station_m: float = float(
            np.linalg.norm(BASE_STATION_POSITION - self.position)
        )

        self.target_node_id: Optional[int] = None
        self.cluster_member_ids: list[int] = []
        self.last_ch_round: int = -1000

    def clone(self) -> "Node":
        new_node = Node(self.id, self.position.copy())
        new_node.remaining_energy_j = self.remaining_energy_j
        new_node.is_alive = self.is_alive
        new_node.is_cluster_head = self.is_cluster_head
        new_node.is_eligible_for_ch = self.is_eligible_for_ch
        new_node.target_node_id = self.target_node_id
        new_node.cluster_member_ids = self.cluster_member_ids.copy()
        new_node.last_ch_round = self.last_ch_round
        return new_node

    @staticmethod
    def create_wsn(width: float, height: float, n_nodes: int, seed: int | None = None) -> list["Node"]:
        rng = np.random.default_rng(seed)
        nodes: list[Node] = []

        for i in range(n_nodes):
            x = rng.uniform(1.0, width)
            y = rng.uniform(1.0, height)
            nodes.append(Node(i, np.array([x, y], dtype=np.float32)))

        return nodes