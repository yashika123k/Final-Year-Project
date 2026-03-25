from node import Node
from config import (
    ENERGY_AGGREGATION_J,
    ENERGY_PER_BIT_ELECTRONICS_J,
    ENERGY_FREE_SPACE_AMP_J,
    ENERGY_MULTIPATH_AMP_J,
    FS_MULTIPATH_THRESHOLD_DISTANCE_M,
)


def calculate_transmit_energy(data_size_bits: float, distance_m: float) -> float:
    """Energy to transmit data over a given distance (first-order radio model)."""
    energy = data_size_bits * ENERGY_PER_BIT_ELECTRONICS_J
    if distance_m <= FS_MULTIPATH_THRESHOLD_DISTANCE_M:
        energy += data_size_bits * ENERGY_FREE_SPACE_AMP_J * (distance_m ** 2)
    else:
        energy += data_size_bits * ENERGY_MULTIPATH_AMP_J * (distance_m ** 4)
    return energy


def calculate_receive_energy(data_size_bits: float) -> float:
    """Energy to receive data (electronics only)."""
    return data_size_bits * ENERGY_PER_BIT_ELECTRONICS_J


def calculate_aggregation_energy(data_size_bits: float) -> float:
    """Energy for a CH to aggregate data from members."""
    return data_size_bits * ENERGY_AGGREGATION_J


def reset_node_for_new_round(node: Node) -> None:
    """Resets protocol state of a node at the start of each round."""
    node.is_cluster_head = False
    node.taregt_node_id = None
    node.cluster_member_ids = []
