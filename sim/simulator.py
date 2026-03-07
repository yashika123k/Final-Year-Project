import random
import pygame

from node import Node
from config import SENSOR_RADIUS, TO_PIXEL_SCALE


class Simulator:

    def __init__(self, width, height, n_nodes, algorithm):

        self.wsn = []
        self.round = 0
        self.alive_count = n_nodes
        self.algorithm = algorithm

        # create nodes
        for node_id in range(n_nodes):

            x = random.uniform(1.0, width)
            y = random.uniform(1.0, height)

            node = Node(node_id, (x, y))
            self.wsn.append(node)

    def step(self):

        self.round += 1

        # run protocol
        self.algorithm.run(self.wsn, self.round)

        # update alive count
        self.alive_count = sum(node.is_alive for node in self.wsn)

    def render(self, screen):

        for node in self.wsn:

            if not node.is_alive:
                color = (180, 60, 60)      # dead
            elif node.is_cluster_head:
                color = (89, 172, 119)     # cluster head
            else:
                color = (245, 235, 200)    # normal node

            x = node.position[0] * TO_PIXEL_SCALE[0]
            y = node.position[1] * TO_PIXEL_SCALE[1]

            pygame.draw.circle(
                screen,
                color,
                (int(x), int(y)),
                int(SENSOR_RADIUS)
            )
