from node import Node
from config import (
    ENERGY_AGGREGATION_J,
    ENERGY_PER_BIT_ELECTRONICS_J,
    ENERGY_FREE_SPACE_AMP_J,
    ENERGY_MULTIPATH_AMP_J,
    FS_MULTIPATH_THRESHOLD_DISTANCE_M,
)


def calculate_transmit_energy(data_size_bits: float, distance_m: float) -> float:
    energy = data_size_bits * ENERGY_PER_BIT_ELECTRONICS_J
    if distance_m <= FS_MULTIPATH_THRESHOLD_DISTANCE_M:
        energy += data_size_bits * ENERGY_FREE_SPACE_AMP_J * (distance_m ** 2)
    else:
        energy += data_size_bits * ENERGY_MULTIPATH_AMP_J * (distance_m ** 4)
    return energy


def calculate_receive_energy(data_size_bits: float) -> float:
    return data_size_bits * ENERGY_PER_BIT_ELECTRONICS_J


def calculate_aggregation_energy(data_size_bits: float) -> float:
    return data_size_bits * ENERGY_AGGREGATION_J


def reset_node_for_new_round(node: Node) -> None:
    node.is_cluster_head = False
    node.target_node_id = None
    node.cluster_member_ids = []


def clamp_and_update_liveness(node: Node) -> bool:
    if node.remaining_energy_j <= 0.0:
        node.remaining_energy_j = 0.0
        if node.is_alive:
            node.is_alive = False
            return True
    return False
