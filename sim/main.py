import pygame

from simulator import Simulator
from protocol import LEACH
from config import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    AREA_WIDTH,
    AREA_HEIGHT,
    NUM_NODES,
    CH_PROBABILITY,
    FPS
)

pygame.init()

screen = pygame.display.set_mode((int(SCREEN_WIDTH), int(SCREEN_HEIGHT)))
pygame.display.set_caption("WSN LEACH Simulation")

clock = pygame.time.Clock()

# protocol
leach = LEACH(CH_PROBABILITY)

# simulator
sim = Simulator(
    AREA_WIDTH,
    AREA_HEIGHT,
    NUM_NODES,
    leach
)

running = True

while running:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # simulation step
    sim.step()

    # render
    screen.fill((30, 30, 30))
    sim.render(screen)

    pygame.display.flip()

    clock.tick(FPS)

pygame.quit()
