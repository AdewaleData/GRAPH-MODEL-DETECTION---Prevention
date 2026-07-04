"""Multi-seed experiment runner with statistical aggregation."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

from .config import DEVICE, EXPERIMENT_SEEDS, EXPERIMENTS_DIR, GNN_BATCH_SIZE, GNN_EPOCHS, GNN_PATIENCE, MAX_FLOWS
from .data_loader import load_cic_ddos, stratified_sample
from .evaluation import evaluate_flow_level_from_graphs, evaluate_gnn_graph, evaluate_sklearn, log_report
from .graph_dataset import (
    build_flow_graphs,
    build_graph_splits,
    compute_class_weights,
    rf_window_baseline,
    split_victim_holdout,
)
from .metrics import compare_seeds_paired, seed_aggregate
from .models import GATGraphClassifier, GCNGraphClassifier
from .preprocessing import clean_dataframe, engineer_features, get_feature_columns, prepare_tabular
from .training import (
    hyperparameter_grid_batched,
    inference_latency_ms,
    predict_graphs,
    train_gnn_batched,
    tune_threshold,
)

logger = logging.getLogger(__name__)


def _set_seed(seed: int) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def run_single_seed(df, feature_cols: list[str], seed: int) -> dict[str, Any]:
    _set_seed(seed)
    X, y, feature_cols, scaler = prepare_tabular(df, feature_cols)
    train_g, val_g, test_g, weights, tr_idx, va_idx, te_idx = build_graph_splits(df, X, seed=seed)
    in_ch = train_g[0].x.shape[1]

    rf = RandomForestClassifier(n_estimators=100, random_state=seed, n_jobs=-1)
    rf.fit(X[tr_idx], y[tr_idx])

    gcn = GCNGraphClassifier(in_ch, hidden_channels=64, num_layers=3, dropout=0.3).to(DEVICE)
    train_gnn_batched(gcn, train_g, val_g, DEVICE, weights, batch_size=GNN_BATCH_SIZE, epochs=GNN_EPOCHS, patience=GNN_PATIENCE)

    gat = GATGraphClassifier(in_ch, hidden_channels=48, heads=4, dropout=0.3).to(DEVICE)
    train_gnn_batched(gat, train_g, val_g, DEVICE, weights, batch_size=GNN_BATCH_SIZE, epochs=GNN_EPOCHS, patience=GNN_PATIENCE)

    thr_gcn, _ = tune_threshold(gcn, val_g, DEVICE, GNN_BATCH_SIZE)
    thr_gat, _ = tune_threshold(gat, val_g, DEVICE, GNN_BATCH_SIZE)

    y_test_flow = y[te_idx]
    X_test = X[te_idx]
    rf_prob = rf.predict_proba(X_test)[:, 1]

    res_rf = evaluate_sklearn("RF (flow)", y_test_flow, y_prob=rf_prob)
    res_gcn = evaluate_gnn_graph("GCN (graph)", gcn, test_g, DEVICE, GNN_BATCH_SIZE,
                                 inference_latency_ms(gcn, test_g, DEVICE, GNN_BATCH_SIZE), thr_gcn)
    res_gat = evaluate_gnn_graph("GAT (graph)", gat, test_g, DEVICE, GNN_BATCH_SIZE,
                                 inference_latency_ms(gat, test_g, DEVICE, GNN_BATCH_SIZE), thr_gat)

    y_gcn_p, _ = predict_graphs(gcn, test_g, DEVICE, GNN_BATCH_SIZE)
    res_gcn_flow = evaluate_flow_level_from_graphs("GCN (flow-mapped)", test_g, y_gcn_p, y_test_flow, thr_gcn)

    y_rf_g, p_rf_g = rf_window_baseline(test_g, rf, scaler, X_test)
    res_rf_g = evaluate_sklearn("RF (graph-window)", y_rf_g, y_prob=p_rf_g)

    for r in [res_rf, res_gcn, res_gat, res_gcn_flow, res_rf_g]:
        log_report(r)

    return {
        "seed": seed,
        "results": {
            r.name: r.metrics.to_dict() for r in [res_rf, res_gcn, res_gat, res_gcn_flow, res_rf_g]
        },
        "thresholds": {"gcn": thr_gcn, "gat": thr_gat},
    }


def run_multi_seed_experiment(
    max_flows: int = MAX_FLOWS,
    seeds: list[int] | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    output_dir = output_dir or EXPERIMENTS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    seeds = seeds or EXPERIMENT_SEEDS

    logger.info("Multi-seed experiment | seeds=%s | max_flows=%d", seeds, max_flows)
    df = stratified_sample(clean_dataframe(engineer_features(load_cic_ddos())), max_flows)
    feature_cols = get_feature_columns(df)

    runs = [run_single_seed(df, feature_cols, s) for s in seeds]
    model_names = list(runs[0]["results"].keys())
    aggregated = {mn: seed_aggregate([r["results"][mn] for r in runs]) for mn in model_names}

    gcn_f1 = [r["results"]["GCN (graph)"]["f1"] for r in runs]
    rf_f1 = [r["results"]["RF (flow)"]["f1"] for r in runs]
    ttest = compare_seeds_paired(gcn_f1, rf_f1)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "max_flows": max_flows,
        "seeds": seeds,
        "aggregated_mean_std": aggregated,
        "paired_ttest_gcn_graph_vs_rf_flow_f1": ttest,
    }
    path = output_dir / "results.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info("Saved %s", path)
    return report


def run_victim_holdout_experiment(df, feature_cols: list[str], seed: int = 42) -> dict[str, Any]:
    _set_seed(seed)
    train_df, test_df = split_victim_holdout(df)
    X_tr, y_tr, _, _ = prepare_tabular(train_df, feature_cols)
    X_te, y_te, _, _ = prepare_tabular(test_df, feature_cols)

    train_g = build_flow_graphs(train_df, X_tr, y_tr)
    test_g = build_flow_graphs(test_df, X_te, y_te)
    if len(train_g) < 10 or len(test_g) < 5:
        return {"error": "insufficient graphs for hold-out"}

    weights = compute_class_weights(train_g)
    in_ch = train_g[0].x.shape[1]
    split = max(1, len(train_g) // 10)
    val_g, tr_g = train_g[:split], train_g[split:]

    gcn = GCNGraphClassifier(in_ch).to(DEVICE)
    train_gnn_batched(gcn, tr_g, val_g, DEVICE, weights, batch_size=GNN_BATCH_SIZE, epochs=40, patience=8)
    thr, _ = tune_threshold(gcn, val_g, DEVICE, GNN_BATCH_SIZE)
    res = evaluate_gnn_graph("GCN (unseen victims)", gcn, test_g, DEVICE, GNN_BATCH_SIZE, threshold=thr)
    log_report(res)
    return {"metrics": res.metrics.to_dict(), "n_test_graphs": len(test_g)}
