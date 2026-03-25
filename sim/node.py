import numpy as np
from typing import Optional
from config import (
    INITIAL_NODE_ENERGY_J,
    BASE_STATION_POSITION,
)

class Node:
    """Represents a single sensor node in the WSN simulation."""

    def __init__(self, node_id: int, position: np.ndarray):
        self.id = node_id
        self.position = position.astype(np.float32)
        self.remaining_energy_j: float = INITIAL_NODE_ENERGY_J
        self.is_alive: bool = True
        self.is_cluster_head: bool = False
        self.is_eligible_for_ch: bool = True
        self.distance_to_base_station_m: float = float(np.linalg.norm(BASE_STATION_POSITION - self.position))
        self.taregt_node_id: Optional[int] = None 
        self.cluster_member_ids: list[int] = []
        self.last_ch_round = -1000

    @staticmethod
    def create_wsn(width: float, height: float, n_nodes: int) -> list[Node]:
        """Creates a WSN with n_nodes randomly placed nodes."""
        rng = np.random.default_rng()
        nodes = []
        for i in range(n_nodes):
            x = rng.uniform(1.0, width)
            y = rng.uniform(1.0, height)
            nodes.append(Node(i, np.array([x, y], dtype=np.float32)))
        return nodes
