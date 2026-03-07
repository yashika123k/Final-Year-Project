import math
from config import INITIAL_ENERGY,SINK


class Node:

    def __init__(self, id: int, position: tuple[float,float]):
        self.id = id
        self.position = position
        self.res_energy = INITIAL_ENERGY

        self.is_alive = True
        self.is_cluster_head = False
        self.is_eligible = True

        # distance to sink computed here directly
        x, y = position
        sx, sy = SINK
        self.distance_to_sink = math.sqrt((x - sx)**2 + (y - sy)**2)

        self.cluster_head_id = None
        self.cluster_members = []


