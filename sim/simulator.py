from __future__ import annotations
from abc import ABC, abstractmethod
import pygame

from node import Node
from config import (
    SENSOR_VISUAL_RADIUS_PX,
    METERS_TO_PIXELS_X,
    METERS_TO_PIXELS_Y,
    BASE_STATION_POSITION,
)


class Protocol(ABC):
    @abstractmethod
    def run_round(self, simulator: "Simulator") -> None: ...

    @abstractmethod
    def name(self) -> str: ...


class Simulator:
    """Central simulation state."""

    def __init__(self, width: float, height: float, node_count: int):
        self.nodes: list[Node] = Node.create_wsn(width, height, node_count)
        self.current_round: int = 0
        self.alive_node_count: int = node_count

        self.alive_history: list[int] = []
        self.energy_history: list[float] = []

    def update(self, protocol: Protocol) -> None:
        self.current_round += 1
        protocol.run_round(self)

        total_energy = sum(node.remaining_energy_j for node in self.nodes)

        self.alive_history.append(self.alive_node_count)
        self.energy_history.append(total_energy)

    def render(self, screen: pygame.Surface) -> None:
        COLOR_DEAD   = (180, 60, 60)
        COLOR_CH     = (89, 172, 119)
        COLOR_NORMAL = (245, 235, 200)
        COLOR_BS     = (100, 180, 255)
        COLOR_LINK   = (80, 80, 100)

        # Draw links
        for node in self.nodes:
            if not node.is_alive:
                continue
            sx = int(node.position[0] * METERS_TO_PIXELS_X)
            sy = int(node.position[1] * METERS_TO_PIXELS_Y)

            if node.is_cluster_head:
                bsx = int(BASE_STATION_POSITION[0] * METERS_TO_PIXELS_X)
                bsy = int(BASE_STATION_POSITION[1] * METERS_TO_PIXELS_Y)
                pygame.draw.line(screen, (60, 120, 80), (sx, sy), (bsx, bsy), 1)
            elif node.cluster_head_id is not None:
                ch = self.nodes[node.cluster_head_id]
                cx = int(ch.position[0] * METERS_TO_PIXELS_X)
                cy = int(ch.position[1] * METERS_TO_PIXELS_Y)
                pygame.draw.line(screen, COLOR_LINK, (sx, sy), (cx, cy), 1)

        # Draw nodes
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

        # Draw base station
        bsx = int(BASE_STATION_POSITION[0] * METERS_TO_PIXELS_X)
        bsy = int(BASE_STATION_POSITION[1] * METERS_TO_PIXELS_Y)
        pygame.draw.rect(screen, COLOR_BS, (bsx - 10, bsy - 10, 20, 20))
