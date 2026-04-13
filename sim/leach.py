import random
import numpy as np

from node import Node
from simulator import Simulator
from utils import (
    reset_node_for_new_round,
    calculate_transmit_energy,
    calculate_receive_energy,
    calculate_aggregation_energy,
    clamp_and_update_liveness,
)
from config import DATA_PACKET_SIZE_BITS


class Leach:
    def __init__(self, cluster_head_probability: float):
        self.cluster_head_probability = cluster_head_probability
        self.cycle_length_rounds = int(1.0 / cluster_head_probability)
        self.election_threshold: float = 0.0

    def name(self) -> str:
        return "LEACH"

    def _update_election_threshold(self, current_round: int) -> None:
        r_mod = current_round % self.cycle_length_rounds
        denom = 1.0 - self.cluster_head_probability * r_mod
        self.election_threshold = min(self.cluster_head_probability / max(denom, 1e-12), 1.0)

    @staticmethod
    def _form_clusters(simulator: Simulator, cluster_head_ids: list[int]) -> None:
        nodes = simulator.nodes

        for node in nodes:
            if not node.is_alive or node.is_cluster_head:
                continue

            min_dist = float("inf")
            nearest_ch_id = None

            for ch_id in cluster_head_ids:
                ch = nodes[ch_id]
                if not ch.is_alive:
                    continue
                dist = float(np.linalg.norm(node.position - ch.position))
                if dist < min_dist:
                    min_dist = dist
                    nearest_ch_id = ch_id

            if nearest_ch_id is not None:
                node.target_node_id = nearest_ch_id
                nodes[nearest_ch_id].cluster_member_ids.append(node.id)
                node.remaining_energy_j -= calculate_transmit_energy(DATA_PACKET_SIZE_BITS, min_dist)

                if clamp_and_update_liveness(node):
                    simulator.alive_node_count -= 1

    def run_round(self, simulator: Simulator) -> None:
        self._update_election_threshold(simulator.current_round)
        selected_ch_ids: list[int] = []

        for node in simulator.nodes:
            reset_node_for_new_round(node)

            if simulator.current_round % self.cycle_length_rounds == 0:
                node.is_eligible_for_ch = True

            if node.is_alive and node.remaining_energy_j <= 0.0:
                node.is_alive = False
                simulator.alive_node_count -= 1
                continue

            if (
                node.is_alive
                and node.is_eligible_for_ch
                and random.random() < self.election_threshold
            ):
                node.is_cluster_head = True
                node.is_eligible_for_ch = False
                selected_ch_ids.append(node.id)

        self._form_clusters(simulator, selected_ch_ids)

        for ch_id in selected_ch_ids:
            ch = simulator.nodes[ch_id]
            if not ch.is_alive:
                continue

            member_count = len(ch.cluster_member_ids)

            ch.remaining_energy_j -= (
                calculate_receive_energy(DATA_PACKET_SIZE_BITS)
                + calculate_aggregation_energy(DATA_PACKET_SIZE_BITS)
            ) * member_count

            ch.remaining_energy_j -= calculate_transmit_energy(
                DATA_PACKET_SIZE_BITS,
                ch.distance_to_base_station_m
            )

            if clamp_and_update_liveness(ch):
                simulator.alive_node_count -= 1