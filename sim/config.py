import numpy as np

# =============================================================================
# Simulation Area & Visualization
# =============================================================================
DEPLOYMENT_AREA_WIDTH_M: float = 500.0
DEPLOYMENT_AREA_HEIGHT_M: float = 500.0

VISUALIZATION_WIDTH_PX: int = 1200
VISUALIZATION_HEIGHT_PX: int = 720

METERS_TO_PIXELS_X: float = VISUALIZATION_WIDTH_PX / DEPLOYMENT_AREA_WIDTH_M
METERS_TO_PIXELS_Y: float = VISUALIZATION_HEIGHT_PX / DEPLOYMENT_AREA_HEIGHT_M

TARGET_FPS: int = 10
SENSOR_VISUAL_RADIUS_PX: int = 8

# =============================================================================
# LEACH Protocol Parameters
# =============================================================================
TOTAL_SENSOR_NODES: int = 100
CLUSTER_HEAD_PROBABILITY: float = 0.1
EXPECTED_NUM_CLUSTER_HEADS: int = int(np.ceil(TOTAL_SENSOR_NODES * CLUSTER_HEAD_PROBABILITY))
CLUSTER_HEAD_CYCLE_LENGTH_ROUNDS: int = int(1.0 / CLUSTER_HEAD_PROBABILITY)

# =============================================================================
# First-Order Radio Energy Model Parameters
# =============================================================================
INITIAL_NODE_ENERGY_J: float = 2.0
ENERGY_PER_BIT_ELECTRONICS_J: float = 5e-8
ENERGY_FREE_SPACE_AMP_J: float = 1e-11
ENERGY_MULTIPATH_AMP_J: float = 1.3e-15
ENERGY_AGGREGATION_J: float = 5e-9
DATA_PACKET_SIZE_BITS: float = 4000.0

# =============================================================================
# Radio Propagation & Threshold
# =============================================================================
FS_MULTIPATH_THRESHOLD_DISTANCE_M: float = 87.7

# =============================================================================
# Base Station (Sink)
# =============================================================================
BASE_STATION_POSITION = np.array([DEPLOYMENT_AREA_WIDTH_M / 2.0, DEPLOYMENT_AREA_HEIGHT_M / 2.0], dtype=np.float32)

# =============================================================================
# Simulation Control
# =============================================================================
MAX_SIMULATION_ROUNDS: int = 2000
TARGET_SIMULATION_STEPS_PER_SECOND: float = 10.0
