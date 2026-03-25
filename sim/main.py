import sys
import csv
import time
import pygame

from config import (
    VISUALIZATION_WIDTH_PX,
    VISUALIZATION_HEIGHT_PX,
    TARGET_FPS,
    TARGET_SIMULATION_STEPS_PER_SECOND,
    DEPLOYMENT_AREA_WIDTH_M,
    DEPLOYMENT_AREA_HEIGHT_M,
    TOTAL_SENSOR_NODES,
    CLUSTER_HEAD_PROBABILITY,
    MAX_SIMULATION_ROUNDS,
)
from simulator import Simulator
from leach import Leach
from zcr import Zcr



BG_COLOR  = (24, 22, 22)
BTN_COLOR = (60, 100, 160)
BTN_HOVER = (80, 130, 200)


def draw_menu(screen: pygame.Surface):
    screen.fill(BG_COLOR)

    btns = {}
    for i, label in enumerate(["LEACH", "ZCR"]):
        rect = pygame.Rect(
            VISUALIZATION_WIDTH_PX // 2 - 100,
            310 + i * 80,
            200, 50
        )
        mx, my = pygame.mouse.get_pos()
        color = BTN_HOVER if rect.collidepoint(mx, my) else BTN_COLOR

        pygame.draw.rect(screen, color, rect, border_radius=8)


        btns[label] = rect

    return btns


def run_simulation(protocol_name: str):
    pygame.display.set_caption(f"WSN Simulator — {protocol_name}")
    screen = pygame.display.set_mode((VISUALIZATION_WIDTH_PX, VISUALIZATION_HEIGHT_PX))
    clock = pygame.time.Clock()

    simulator = Simulator(DEPLOYMENT_AREA_WIDTH_M, DEPLOYMENT_AREA_HEIGHT_M, TOTAL_SENSOR_NODES)

    if protocol_name == "LEACH":
        protocol = Leach(CLUSTER_HEAD_PROBABILITY)
        csv_filename = "leach.csv"
    else:
        protocol = Zcr(CLUSTER_HEAD_PROBABILITY)
        csv_filename = "zcr.csv"

    csv_file = open(csv_filename, "w", newline="")
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(["round", "alive_nodes", "node_id", "remaining_energy_j"])

    fixed_timestep = 1.0 / TARGET_SIMULATION_STEPS_PER_SECOND
    time_accumulator = 0.0
    last_time = time.perf_counter()
    paused = False

    running = True
    while running:
        now = time.perf_counter()
        delta = now - last_time
        last_time = now

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    csv_file.close()
                    run_simulation(protocol_name)
                    return

        if not paused and simulator.alive_node_count > 0 and simulator.current_round < MAX_SIMULATION_ROUNDS:
            time_accumulator += delta
            while time_accumulator >= fixed_timestep:
                simulator.update(protocol)
                for node in simulator.nodes:
                    csv_writer.writerow([
                        simulator.current_round,
                        simulator.alive_node_count,
                        node.id,
                        round(node.remaining_energy_j, 6),
                    ])
                time_accumulator -= fixed_timestep

        screen.fill(BG_COLOR)

        simulator.render(screen,protocol)


        pygame.display.flip()
        clock.tick(TARGET_FPS)

    csv_file.close()


def main():
    pygame.init()
    screen = pygame.display.set_mode((VISUALIZATION_WIDTH_PX, VISUALIZATION_HEIGHT_PX))
    pygame.display.set_caption("WSN Simulator")
    clock = pygame.time.Clock()

    chosen: str | None = None

    while chosen is None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                btns = draw_menu(screen)
                for label, rect in btns.items():
                    if rect.collidepoint(event.pos):
                        chosen = label

        draw_menu(screen)
        pygame.display.flip()
        clock.tick(60)

    run_simulation(chosen)
    pygame.quit()


if __name__ == "__main__":
    main()
