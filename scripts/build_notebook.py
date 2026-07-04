"""Generate the FYP Jupyter notebook."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NB_PATH = ROOT / "notebooks" / "CICDDoS_GNN_DDoS_Detection.ipynb"


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": [text]}


def py(text: str) -> dict:
    return {
        "cell_type": "code",
        "metadata": {},
        "source": [text],
        "outputs": [],
        "execution_count": None,
    }


cells: list[dict] = []

cells.append(
    md(
        """# Real-Time DDoS Attack Detection Using Graph Neural Networks
## CICDDoS2019 Dataset — Final Year Project

**Stack:** PyTorch · PyTorch Geometric · NetworkX · Scikit-learn · XGBoost

This notebook implements a production-grade pipeline: preprocessing → graph construction → GCN/GAT + baselines → evaluation → deployment artifacts.

> LAN simulation is **not** included. Only **CICDDoS2019**."""
    )
)

cells.append(
    md(
        """## 1. Problem Definition

**Goal:** Detect DDoS attacks from network flow records in near real time.

**Graph formulation:** Each IP is a **node**; each flow is a directed **edge** (source → destination). Node features aggregate flow statistics; labels indicate malicious involvement.

| DSA Concept | Usage |
|-------------|--------|
| Graph | IP-flow communication topology |
| Hash map | O(1) IP → node index |
| Arrays | Features, labels, masks |
| Matrices | Feature matrix **X**, sparse adjacency |
| BFS / DFS | Subgraph viz & attack-region traversal |
| Adjacency | PyG `edge_index` (COO sparse format) |
| Priority (concept) | GAT attention ranks neighbors |"""
    )
)

cells.append(md("## 2. Environment Setup"))
cells.append(
    py(
        """import logging
import sys
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path.cwd().resolve()
if not (PROJECT_ROOT / "src").exists() and (PROJECT_ROOT.parent / "src").exists():
    PROJECT_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ddos_gnn.config import ARTIFACTS_DIR, DATA_PATH, DEVICE, FIGURES_DIR, MAX_FLOWS, MODELS_DIR, RANDOM_SEED
from ddos_gnn.inference import ensure_artifact_dirs

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("ddos_gnn_notebook")

np.random.seed(RANDOM_SEED)
torch.manual_seed(RANDOM_SEED)
ensure_artifact_dirs(ARTIFACTS_DIR, MODELS_DIR, FIGURES_DIR)
logger.info("Device: %s | MAX_FLOWS=%s", DEVICE, MAX_FLOWS)
print(f"PyTorch {torch.__version__} | Device: {DEVICE}")"""
    )
)

cells.append(md("## 3. Dataset Loading"))
cells.append(
    py(
        """from ddos_gnn.data_loader import load_cic_ddos

df_raw = load_cic_ddos(DATA_PATH)
logger.info("Loaded: %s", df_raw.shape)
df_raw.head(3)"""
    )
)

cells.append(md("## 4. Exploratory Data Analysis (EDA)"))
cells.append(
    py(
        """from ddos_gnn.visualization import plot_correlation_heatmap, plot_label_distribution

fig_dist = plot_label_distribution(df_raw, "Label", FIGURES_DIR / "label_distribution.html")
fig_dist.show()
display(df_raw.describe().T.head(12))
df_raw["Label"].value_counts()"""
    )
)

cells.append(md("## 5. Data Cleaning"))
cells.append(
    py(
        """from ddos_gnn.data_loader import stratified_sample
from ddos_gnn.preprocessing import clean_dataframe

df = clean_dataframe(df_raw)
df = stratified_sample(df, MAX_FLOWS)
logger.info("Working set: %s", df.shape)
df["Label"].value_counts()"""
    )
)

cells.append(md("## 6. Feature Engineering"))
cells.append(
    py(
        """from ddos_gnn.preprocessing import engineer_features, get_feature_columns

df = engineer_features(df)
feature_cols = get_feature_columns(df)
logger.info("Features: %d", len(feature_cols))"""
    )
)

cells.append(md("## 7. Data Scaling & Encoding"))
cells.append(
    py(
        """from ddos_gnn.data_loader import binary_labels
from ddos_gnn.preprocessing import prepare_tabular

X, y, feature_cols, scaler = prepare_tabular(df, feature_cols)
y_flow = binary_labels(df["Label"])
logger.info("Feature matrix: %s", X.shape)"""
    )
)

cells.append(md("## 8. Graph Construction (Flow-Window Graphs)"))
cells.append(
    py(
        """from ddos_gnn.config import GNN_BATCH_SIZE, GRAPH_GROUP_COL, GRAPH_MAX_FLOWS, GRAPH_MIN_FLOWS
from ddos_gnn.graph_dataset import build_graph_splits, get_viz_graph

# Scaled flow features -> batched graphs grouped by victim IP (hash map O(n))
train_graphs, val_graphs, test_graphs, class_weights, tr_idx, va_idx, te_idx = build_graph_splits(df, X)
from ddos_gnn.graph_dataset import aligned_tabular_splits
X_train, X_val, X_test, y_train, y_val, y_test = aligned_tabular_splits(X, y_flow, tr_idx, va_idx, te_idx)
in_channels = train_graphs[0].x.shape[1] if train_graphs else X.shape[1]
logger.info("Aligned splits — flows: %d / %d / %d | graphs: %d / %d / %d",
    len(X_train), len(X_val), len(X_test), len(train_graphs), len(val_graphs), len(test_graphs))
logger.info("Graph task: %d train / %d val / %d test | in_channels=%d", len(train_graphs), len(val_graphs), len(test_graphs), in_channels)

# NetworkX subgraph for visualization only
G_viz, ip_indexer = get_viz_graph(df.sample(min(3000, len(df)), random_state=RANDOM_SEED), feature_cols)
logger.info("Viz subgraph: %d nodes (hash-mapped IPs)", G_viz.number_of_nodes())"""
    )
)

cells.append(md("## 9. PyTorch Geometric DataLoader"))
cells.append(
    py(
        """from torch_geometric.loader import DataLoader

train_loader = DataLoader(train_graphs, batch_size=GNN_BATCH_SIZE, shuffle=True)
val_loader = DataLoader(val_graphs, batch_size=GNN_BATCH_SIZE, shuffle=False)
test_loader = DataLoader(test_graphs, batch_size=GNN_BATCH_SIZE, shuffle=False)
sample_batch = next(iter(train_loader))
logger.info("Mini-batch: %d graphs | %d nodes | %d edges", sample_batch.num_graphs, sample_batch.num_nodes, sample_batch.num_edges)
sample_batch"""
    )
)

cells.append(md("## 10. Baseline ML Models"))
cells.append(
    py(
        """import time
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier

logger.info("Training Random Forest...")
rf = RandomForestClassifier(n_estimators=200, random_state=RANDOM_SEED, n_jobs=-1)
rf.fit(X_train, y_train)

logger.info("Training XGBoost...")
xgb = XGBClassifier(n_estimators=200, max_depth=8, learning_rate=0.1, random_state=RANDOM_SEED, n_jobs=-1)
xgb.fit(X_train, y_train)

rf_prob = rf.predict_proba(X_test)[:, 1]
xgb_prob = xgb.predict_proba(X_test)[:, 1]"""
    )
)

cells.append(md("## 11. GCN Model (Graph-Level)"))
cells.append(
    py(
        """from ddos_gnn.config import GNN_EPOCHS, GNN_PATIENCE
from ddos_gnn.models import GCNGraphClassifier

num_classes = 2
gcn = GCNGraphClassifier(in_channels=in_channels, hidden_channels=64, out_channels=num_classes, num_layers=3, dropout=0.3).to(DEVICE)
sum(p.numel() for p in gcn.parameters())"""
    )
)

cells.append(md("## 12. GAT Model (Graph-Level)"))
cells.append(
    py(
        """from ddos_gnn.models import GATGraphClassifier

gat = GATGraphClassifier(in_channels=in_channels, hidden_channels=48, out_channels=num_classes, heads=4, dropout=0.3).to(DEVICE)
sum(p.numel() for p in gat.parameters())"""
    )
)

cells.append(md("## 13. Model Training (Focal Loss + Class Weights + Edge Features)"))
cells.append(
    py(
        """from ddos_gnn.training import inference_latency_ms, train_gnn_batched, tune_threshold

logger.info("Training GCN (focal loss, edge-weighted conv)...")
gcn_history = train_gnn_batched(gcn, train_graphs, val_graphs, DEVICE, class_weights, batch_size=GNN_BATCH_SIZE, epochs=GNN_EPOCHS, patience=GNN_PATIENCE)
logger.info("Training GAT (edge-aware attention)...")
gat_history = train_gnn_batched(gat, train_graphs, val_graphs, DEVICE, class_weights, batch_size=GNN_BATCH_SIZE, epochs=GNN_EPOCHS, patience=GNN_PATIENCE)

gcn_threshold, _ = tune_threshold(gcn, val_graphs, DEVICE, GNN_BATCH_SIZE)
gat_threshold, _ = tune_threshold(gat, val_graphs, DEVICE, GNN_BATCH_SIZE)
logger.info("Tuned thresholds: GCN=%.3f GAT=%.3f", gcn_threshold, gat_threshold)

gcn_latency = inference_latency_ms(gcn, test_graphs, DEVICE, batch_size=GNN_BATCH_SIZE)
gat_latency = inference_latency_ms(gat, test_graphs, DEVICE, batch_size=GNN_BATCH_SIZE)"""
    )
)

cells.append(md("## 14. Hyperparameter Tuning"))
cells.append(
    py(
        """from ddos_gnn.models import GATGraphClassifier, GCNGraphClassifier
from ddos_gnn.training import hyperparameter_grid_batched

gcn_grid = [
    {"hidden_channels": 48, "num_layers": 2, "dropout": 0.2, "lr": 1e-3, "epochs": 30, "patience": 8},
    {"hidden_channels": 64, "num_layers": 3, "dropout": 0.3, "lr": 5e-4, "epochs": 30, "patience": 8},
    {"hidden_channels": 64, "num_layers": 3, "dropout": 0.4, "lr": 1e-3, "epochs": 30, "patience": 8},
]
gcn_tuned, gcn_best_params, gcn_tune_history = hyperparameter_grid_batched(
    GCNGraphClassifier, train_graphs, val_graphs, DEVICE, class_weights, in_channels, gcn_grid, batch_size=GNN_BATCH_SIZE,
)
logger.info("Best GCN: %s", gcn_best_params)

gat_grid = [
    {"hidden_channels": 32, "dropout": 0.2, "lr": 1e-3, "epochs": 30, "patience": 8},
    {"hidden_channels": 48, "dropout": 0.3, "lr": 5e-4, "epochs": 30, "patience": 8},
]
gat_tuned, gat_best_params, gat_tune_history = hyperparameter_grid_batched(
    GATGraphClassifier, train_graphs, val_graphs, DEVICE, class_weights, in_channels, gat_grid, batch_size=GNN_BATCH_SIZE,
)
logger.info("Best GAT: %s", gat_best_params)"""
    )
)

cells.append(md("## 15. Evaluation Metrics (Extended + Fair Comparison)"))
cells.append(
    py(
        """import time
from ddos_gnn.evaluation import evaluate_flow_level_from_graphs, evaluate_gnn_graph, evaluate_sklearn, log_report, significance_table
from ddos_gnn.graph_dataset import rf_window_baseline
from ddos_gnn.training import predict_graphs

t0 = time.perf_counter()
for _ in range(100):
    rf.predict_proba(X_test[:1])
rf_latency = (time.perf_counter() - t0) / 100 * 1000
t0 = time.perf_counter()
for _ in range(100):
    xgb.predict_proba(X_test[:1])
xgb_latency = (time.perf_counter() - t0) / 100 * 1000

results = [
    evaluate_sklearn("RF (per-flow)", y_test, y_prob=rf_prob, latency_ms=rf_latency),
    evaluate_sklearn("XGBoost (per-flow)", y_test, y_prob=xgb_prob, latency_ms=xgb_latency),
    evaluate_gnn_graph("GCN (graph)", gcn_tuned, test_graphs, DEVICE, GNN_BATCH_SIZE, gcn_latency, gcn_threshold),
    evaluate_gnn_graph("GAT (graph)", gat_tuned, test_graphs, DEVICE, GNN_BATCH_SIZE, gat_latency, gat_threshold),
]

# Fair graph-window RF baseline (same windows as GNN)
y_rf_g, p_rf_g = rf_window_baseline(test_graphs, rf, scaler, X_test)
results.append(evaluate_sklearn("RF (graph-window)", y_rf_g, y_prob=p_rf_g))

# Flow-level GNN via graph prediction propagation
y_gcn_p, _ = predict_graphs(gcn_tuned, test_graphs, DEVICE, GNN_BATCH_SIZE)
results.append(evaluate_flow_level_from_graphs("GCN (flow-mapped)", test_graphs, y_gcn_p, y_test, gcn_threshold))

for r in results:
    log_report(r)
graph_results = [r for r in results if "graph" in r.name.lower() and "mapped" not in r.name.lower()]
print(significance_table(graph_results[0].y_true, graph_results, reference="RF (graph-window)"))"""
    )
)

cells.append(md("## 16. Model Comparison & Visualizations"))
cells.append(
    py(
        """from ddos_gnn.evaluation import comparison_table
from ddos_gnn.graph_builder import dfs_attack_region
from ddos_gnn.visualization import (
    plot_confusion_matrix,
    plot_feature_importance,
    plot_graph_network,
    plot_pr_curve,
    plot_realtime_attack_highlight,
    plot_roc_curve,
    plot_training_curves,
    plot_correlation_heatmap,
)

print(comparison_table(results))
plot_correlation_heatmap(X_train, feature_cols, top_k=20, save_path=FIGURES_DIR / "correlation.png")
plt.show()
plot_feature_importance(rf.feature_importances_, feature_cols, save_path=FIGURES_DIR / "importance.png")
plt.show()
plot_training_curves(gcn_tune_history, "GCN Tuning Loss", FIGURES_DIR / "gcn_loss.html").show()
plot_training_curves(gat_tune_history, "GAT Tuning Loss", FIGURES_DIR / "gat_loss.html").show()

plot_confusion_matrix(results[0].confusion, "Random Forest CM", FIGURES_DIR / "cm_rf.png")
plt.show()
plot_roc_curve(results[0].y_true, results[0].y_prob, "Random Forest ROC", FIGURES_DIR / "roc_rf.png")
plt.show()
plot_pr_curve(results[0].y_true, results[0].y_prob, "RF PR", FIGURES_DIR / "pr_rf.png")
plt.show()

best_gnn = max([r for r in results if "GCN" in r.name or "GAT" in r.name], key=lambda r: r.f1)
plot_pr_curve(best_gnn.y_true, best_gnn.y_prob, f"{best_gnn.name} PR", FIGURES_DIR / "pr_gnn.png")
plt.show()
plot_confusion_matrix(best_gnn.confusion, f"{best_gnn.name} CM", FIGURES_DIR / "cm_gnn.png")
plt.show()
plot_roc_curve(best_gnn.y_true, best_gnn.y_prob, f"{best_gnn.name} ROC", FIGURES_DIR / "roc_gnn.png")
plt.show()

node_label_map = {n: int(d.get("attack", 0)) for n, d in G_viz.nodes(data=True)}
plot_graph_network(G_viz, node_label_map, save_path=FIGURES_DIR / "graph.png")
plt.show()
attack_region = dfs_attack_region(G_viz)
plot_realtime_attack_highlight(G_viz, attack_region, save_path=FIGURES_DIR / "attack_highlight.png")
plt.show()"""
    )
)

cells.append(md("## 17. Real-Time Inference Preparation"))
cells.append(
    py(
        """from ddos_gnn.inference import predict_flow_sklearn, save_gnn_model, save_sklearn_bundle

bundle = {"model": rf, "scaler": scaler, "feature_cols": feature_cols}
pred, prob = predict_flow_sklearn(bundle, X_test[0])
logger.info("Sample flow: %s (p=%.4f)", "DDoS" if pred else "BENIGN", prob)

metadata = {"feature_cols": feature_cols, "in_channels": in_channels, "num_classes": num_classes, "model_type": "GCNGraph", "graph_level": True, "batch_size": GNN_BATCH_SIZE, "threshold": gcn_threshold}
save_gnn_model(MODELS_DIR / "gcn_best.pt", gcn_tuned, metadata)
save_sklearn_bundle(MODELS_DIR / "rf_bundle.joblib", rf, scaler, feature_cols)

# Example: predict on one test graph window
from ddos_gnn.inference import predict_graph_batch
gp, gprob = predict_graph_batch(gcn_tuned, test_graphs[:4], DEVICE, batch_size=4)
logger.info("Sample graph predictions: %s", list(zip(gp, [round(p, 3) for p in gprob])))"""
    )
)

cells.append(md("## 18. Model Serialization"))
cells.append(
    py(
        """import joblib
from ddos_gnn.inference import save_gnn_model

joblib.dump(feature_cols, MODELS_DIR / "feature_cols.joblib")
save_gnn_model(MODELS_DIR / "gat_best.pt", gat_tuned, {**metadata, "model_type": "GATGraph"})
logger.info("Artifacts saved to %s", MODELS_DIR)"""
    )
)

cells.append(md("## 19. Multi-Seed Experiments & Statistical Significance"))
cells.append(
    py(
        """from ddos_gnn.config import EXPERIMENT_SEEDS
from ddos_gnn.experiments import run_multi_seed_experiment, run_victim_holdout_experiment

# 3 seeds for notebook runtime (full study: EXPERIMENT_SEEDS in config)
report = run_multi_seed_experiment(max_flows=MAX_FLOWS, seeds=EXPERIMENT_SEEDS[:3])
print("=== Aggregated metrics (mean ± std) ===")
for model, stats in report["aggregated_mean_std"].items():
    f1 = stats.get("f1", {})
    print(f"{model}: F1={f1.get('mean', 0):.4f} ± {f1.get('std', 0):.4f}")
print("Paired t-test GCN vs RF (flow) F1:", report["paired_ttest_gcn_graph_vs_rf_flow_f1"])

holdout = run_victim_holdout_experiment(df, feature_cols)
logger.info("Unseen-victim hold-out: %s", holdout)"""
    )
)

cells.append(
    md(
        """## 20. Final Conclusions

1. CICDDoS2019 enables realistic DDoS vs benign flow classification.
2. Flow-window graphs (victim IP groups) + batched GCN/GAT detect attack traffic windows reliably.
3. RF/XGBoost are per-flow baselines; GNNs are per-window graph classifiers with class-weighted training.
4. Metrics (Accuracy, Precision, Recall, F1, ROC-AUC, latency) support comparative analysis.
5. Serialized models are ready for backend integration.

**Future work:** temporal graph windows, inductive GNNs on unseen IPs, ensemble fusion."""
    )
)

notebook = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.11.0"},
    },
    "cells": cells,
}

NB_PATH.parent.mkdir(parents=True, exist_ok=True)
NB_PATH.write_text(json.dumps(notebook, indent=1), encoding="utf-8")
print("Wrote", NB_PATH)
