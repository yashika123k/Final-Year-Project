import random
from config import PACKET_SIZE
from utils import transmission_energy, receive_energy, aggregation_energy, reset_node


class LEACH:

    def __init__(self, probability: float):

        self.p = probability
        self.cycle_length = int(1.0 / probability)
        self.threshold = 0.0

    def update_threshold(self, round: int):

        r_mod = round % self.cycle_length
        denom = 1.0 - self.p * r_mod

        self.threshold = min(self.p / denom, 1.0)

    def form_clusters(self, wsn, cluster_heads):

        for node in wsn:

            if node.is_alive and not node.is_cluster_head:

                min_dist = float("inf")
                nearest_ch = None

                for ch_id in cluster_heads:

                    ch = wsn[ch_id]

                    dx = node.position[0] - ch.position[0]
                    dy = node.position[1] - ch.position[1]

                    dist = (dx*dx + dy*dy) ** 0.5

                    if dist < min_dist:
                        min_dist = dist
                        nearest_ch = ch_id

                if nearest_ch is not None:

                    node.cluster_head_id = nearest_ch
                    wsn[nearest_ch].cluster_members.append(node.id)

                    node.res_energy -= transmission_energy(PACKET_SIZE, min_dist)

    def run(self, wsn, round: int):

        self.update_threshold(round)

        cluster_heads = []

        # first pass
        for node in wsn:

            reset_node(node)

            if round % self.cycle_length == 0:
                node.is_eligible = True

            if node.is_alive and node.res_energy <= 0:
                node.is_alive = False
                continue

            if random.random() < self.threshold and node.is_alive and node.is_eligible:

                node.is_cluster_head = True
                node.is_eligible = False
                cluster_heads.append(node.id)

        # cluster formation
        self.form_clusters(wsn, cluster_heads)

        # cluster head energy dissipation
        for ch_id in cluster_heads:

            ch = wsn[ch_id]

            if not ch.is_alive:
                continue

            k = len(ch.cluster_members)

            ch.res_energy -= (receive_energy(PACKET_SIZE) + aggregation_energy(PACKET_SIZE)) * k
            ch.res_energy -= transmission_energy(PACKET_SIZE, ch.distance_to_sink)
