"""Central configuration for CICDDoS2019 GNN pipeline."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "CICDDoS.csv"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
MODELS_DIR = ARTIFACTS_DIR / "models"
FIGURES_DIR = ARTIFACTS_DIR / "figures"
EXPERIMENTS_DIR = ARTIFACTS_DIR / "experiments"

RANDOM_SEED = 42
EXPERIMENT_SEEDS = [42, 123, 456, 789, 2024]

MAX_FLOWS = 80_000
GRAPH_VIZ_MAX_NODES = 80

DROP_COLUMNS = [
    "Flow ID",
    "Source IP",
    "Destination IP",
    "Timestamp",
    "Label",
]
TARGET_COLUMN = "Label"
BENIGN_LABEL = "BENIGN"
ATTACK_LABEL = "DDoS"

TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

# Flow-window graphs
GRAPH_GROUP_COL = "Destination IP"
GRAPH_MIN_FLOWS = 12
GRAPH_MAX_FLOWS = 48
GRAPH_WINDOW_STRIDE = 48  # non-overlapping windows → less duplicate graphs
GRAPH_MAX_PER_VICTIM = 8
GRAPH_LABEL_MIN_ATTACK_RATIO = 0.5
GRAPH_EXTRA_NODE_FEATURES = 3  # is_victim, is_source, log_degree

# GNN training
GNN_HIDDEN_DIM = 64
GNN_NUM_LAYERS = 3
GNN_DROPOUT = 0.3
GNN_LR = 1e-3
GNN_WEIGHT_DECAY = 5e-4
GNN_EPOCHS = 60
GNN_PATIENCE = 10
GNN_BATCH_SIZE = 64
GNN_USE_FOCAL_LOSS = True
GNN_FOCAL_GAMMA = 2.0
THRESHOLD_METRIC = "f1"

# Statistical reporting
BOOTSTRAP_SAMPLES = 1000
SIGNIFICANCE_ALPHA = 0.05

# Baseline
RF_N_ESTIMATORS = 200
XGB_N_ESTIMATORS = 200
XGB_MAX_DEPTH = 8

# Victim hold-out experiment (fraction of victim IPs held out)
VICTIM_HOLDOUT_RATIO = 0.20

import torch

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
