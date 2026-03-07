from config import (
    E_AGGREGATION,
    E_ELECTRONICS,
    E_FREE_SPACE,
    E_MULTIPATH,
    THRESHOLD_DISTANCE
)


def transmission_energy(packet_size: float, distance: float) -> float:

    energy = packet_size * E_ELECTRONICS

    if distance <= THRESHOLD_DISTANCE:
        energy += packet_size * E_FREE_SPACE * (distance ** 2)
    else:
        energy += packet_size * E_MULTIPATH * (distance ** 4)

    return energy


def reset_node(node):

    node.is_cluster_head = False
    node.cluster_head_id = None
    node.cluster_members.clear()


def receive_energy(packet_size: float) -> float:

    return packet_size * E_ELECTRONICS


def aggregation_energy(packet_size: float) -> float:

    return packet_size * E_AGGREGATION
