"""Smoke test for top-level GNN pipeline."""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
logging.basicConfig(level=logging.INFO, format="%(message)s")

import ddos_gnn.config as cfg

cfg.MAX_FLOWS = 6000
cfg.GNN_EPOCHS = 8
cfg.GNN_BATCH_SIZE = 32
cfg.EXPERIMENT_SEEDS = [42, 123]

from ddos_gnn.config import DATA_PATH, DEVICE, GNN_BATCH_SIZE
from ddos_gnn.data_loader import load_cic_ddos, stratified_sample
from ddos_gnn.evaluation import evaluate_gnn_graph
from ddos_gnn.graph_dataset import build_graph_splits
from ddos_gnn.models import GCNGraphClassifier
from ddos_gnn.preprocessing import clean_dataframe, engineer_features, get_feature_columns, prepare_tabular
from ddos_gnn.training import train_gnn_batched, tune_threshold

df = stratified_sample(clean_dataframe(engineer_features(load_cic_ddos(DATA_PATH))), cfg.MAX_FLOWS)
feature_cols = get_feature_columns(df)
X, y, _, _ = prepare_tabular(df, feature_cols)
train_g, val_g, test_g, weights, *_ = build_graph_splits(df, X)
in_ch = train_g[0].x.shape[1]

model = GCNGraphClassifier(in_ch, hidden_channels=32, num_layers=2).to(DEVICE)
train_gnn_batched(model, train_g, val_g, DEVICE, weights, batch_size=GNN_BATCH_SIZE, epochs=8, patience=3)
thr, _ = tune_threshold(model, val_g, DEVICE, GNN_BATCH_SIZE)
res = evaluate_gnn_graph("GCN", model, test_g, DEVICE, GNN_BATCH_SIZE, threshold=thr)
print(f"F1={res.f1:.4f} MCC={res.metrics.mcc:.4f} PR-AUC={res.metrics.pr_auc:.4f}")
assert res.f1 > 0.55 and res.recall > 0.7
print("Top-level pipeline OK")
