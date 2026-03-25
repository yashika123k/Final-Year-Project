from typing import Protocol
import pygame
from node import Node
from config import (
    SENSOR_VISUAL_RADIUS_PX,
    METERS_TO_PIXELS_X,
    METERS_TO_PIXELS_Y,
    BASE_STATION_POSITION,
    FS_MULTIPATH_THRESHOLD_DISTANCE_M,
)


class Simulator:
    """Central simulation state."""

    def __init__(self, width: float, height: float, node_count: int):
        self.nodes: list[Node] = Node.create_wsn(width, height, node_count)
        self.current_round: int = 0
        self.alive_node_count: int = node_count

        self.alive_history: list[int] = []
        self.energy_history: list[float] = []

    def update(self, protocol) -> None:
        self.current_round += 1
        protocol.run_round(self)

        total_energy = sum(node.remaining_energy_j for node in self.nodes)

        self.alive_history.append(self.alive_node_count)
        self.energy_history.append(total_energy)

    def render(self, screen: pygame.Surface, protocol=None) -> None:
        COLOR_DEAD   = (180, 60, 60)
        COLOR_CH     = (89, 172, 119)
        COLOR_NORMAL = (245, 235, 200)
        COLOR_BS     = (100, 180, 255)
        COLOR_LINK   = (80, 80, 100)
        COLOR_CH_LINK = (60, 120, 80)

        # =======================
        # BASE STATION
        # =======================
        bsx = int(BASE_STATION_POSITION[0] * METERS_TO_PIXELS_X)
        bsy = int(BASE_STATION_POSITION[1] * METERS_TO_PIXELS_Y)

        # =======================
        # DYNAMIC ZONE RADIUS
        # =======================
        if protocol is not None and hasattr(protocol, "current_radius"):
            radius_m = protocol.current_radius
        else:
            radius_m = FS_MULTIPATH_THRESHOLD_DISTANCE_M * 1.5

        zone_radius_px = int(radius_m * METERS_TO_PIXELS_X)

        # =======================
        # DRAW ZONE (DYNAMIC)
        # =======================
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)

        pygame.draw.circle(
            overlay,
            (100, 100, 255, 30),
            (bsx, bsy),
            zone_radius_px
        )

        screen.blit(overlay, (0, 0))

        pygame.draw.circle(
            screen,
            (100, 100, 180),
            (bsx, bsy),
            zone_radius_px,
            2
        )

        # =======================
        # DRAW LINKS
        # =======================
        for node in self.nodes:
            if not node.is_alive:
                continue

            sx = int(node.position[0] * METERS_TO_PIXELS_X)
            sy = int(node.position[1] * METERS_TO_PIXELS_Y)

            if node.taregt_node_id is not None:
                target_node = self.nodes[node.taregt_node_id]

                tx = int(target_node.position[0] * METERS_TO_PIXELS_X)
                ty = int(target_node.position[1] * METERS_TO_PIXELS_Y)

                if node.is_cluster_head:
                    pygame.draw.line(screen, COLOR_CH_LINK, (sx, sy), (tx, ty), 1)
                else:
                    pygame.draw.line(screen, COLOR_LINK, (sx, sy), (tx, ty), 1)
            else:
                pygame.draw.line(screen, COLOR_DEAD, (sx, sy), (bsx, bsy), 1)

        # =======================
        # DRAW NODES
        # =======================
        for node in self.nodes:
            sx = int(node.position[0] * METERS_TO_PIXELS_X)
            sy = int(node.position[1] * METERS_TO_PIXELS_Y)

            if not node.is_alive:
                color, r = COLOR_DEAD, SENSOR_VISUAL_RADIUS_PX - 3
            elif node.is_cluster_head:
                color, r = COLOR_CH, SENSOR_VISUAL_RADIUS_PX + 3
            else:
                color, r = COLOR_NORMAL, SENSOR_VISUAL_RADIUS_PX

            pygame.draw.circle(screen, color, (sx, sy), r)

        # =======================
        # DRAW BASE STATION
        # =======================
        pygame.draw.rect(screen, COLOR_BS, (bsx - 10, bsy - 10, 20, 20))
