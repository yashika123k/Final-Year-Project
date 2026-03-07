import math

# =============================================================================
# Simulation Area & Visualization
# =============================================================================

AREA_WIDTH = 500.0
AREA_HEIGHT = 500.0

SCREEN_WIDTH = 1200.0
SCREEN_HEIGHT = 720.0

# scaling factor (x, y)
TO_PIXEL_SCALE = (
    SCREEN_WIDTH / AREA_WIDTH,
    SCREEN_HEIGHT / AREA_HEIGHT
)

FPS = 10
SENSOR_RADIUS = 10.0


# =============================================================================
# LEACH Protocol Parameters
# =============================================================================

NUM_NODES = 100

CH_PROBABILITY = 0.1

EXPECTED_CLUSTER_HEADS = math.ceil(NUM_NODES * CH_PROBABILITY)

CYCLE_LENGTH = int(1.0 / CH_PROBABILITY)


# =============================================================================
# First-Order Radio Energy Model Parameters
# =============================================================================

INITIAL_ENERGY = 2.0

E_ELECTRONICS = 5e-8
E_FREE_SPACE = 1e-11
E_MULTIPATH = 1.3e-15
E_AGGREGATION = 5e-9

PACKET_SIZE = 4000.0


# =============================================================================
# Radio Propagation & Threshold
# =============================================================================

THRESHOLD_DISTANCE = 87.7


# =============================================================================
# Base Station (Sink)
# =============================================================================

SINK = (
    AREA_WIDTH / 2.0,
    AREA_HEIGHT / 2.0
)


# =============================================================================
# Simulation Control
# =============================================================================

MAX_ROUNDS = 2000
