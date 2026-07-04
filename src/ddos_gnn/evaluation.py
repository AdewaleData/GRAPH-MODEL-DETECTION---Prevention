"""Evaluation with extended metrics, fair baselines, and significance reporting."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import torch
from torch import nn
from torch_geometric.data import Data
from torch_geometric.loader import DataLoader

from .metrics import (
    MetricBundle,
    bootstrap_ci,
    compute_metrics,
    mcnemar_test,
)
from .training import predict_graphs

logger = logging.getLogger(__name__)


@dataclass
class EvalResult:
    name: str
    metrics: MetricBundle
    confusion: np.ndarray
    y_true: np.ndarray
    y_prob: np.ndarray
    y_pred: np.ndarray
    latency_ms: float | None = None
    threshold: float = 0.5
    bootstrap: dict[str, dict[str, float]] = field(default_factory=dict)

    @property
    def accuracy(self) -> float:
        return self.metrics.accuracy

    @property
    def precision(self) -> float:
        return self.metrics.precision

    @property
    def recall(self) -> float:
        return self.metrics.recall

    @property
    def f1(self) -> float:
        return self.metrics.f1

    @property
    def roc_auc(self) -> float:
        return self.metrics.roc_auc


def _bootstrap_report(y_true: np.ndarray, y_prob: np.ndarray) -> dict[str, dict[str, float]]:
    def f1_fn(yt, yp):
        return compute_metrics(yt, (yp >= 0.5).astype(int), yp).f1

    def auc_fn(yt, yp):
        return compute_metrics(yt, None, yp).roc_auc

    out = {}
    for name, fn in [("f1", f1_fn), ("roc_auc", auc_fn)]:
        pt, lo, hi = bootstrap_ci(y_true, y_prob, fn)
        out[name] = {"point": pt, "ci_low": lo, "ci_high": hi}
    return out


def evaluate_sklearn(
    name: str,
    y_true: np.ndarray,
    y_pred: np.ndarray | None = None,
    y_prob: np.ndarray | None = None,
    latency_ms: float | None = None,
    threshold: float = 0.5,
) -> EvalResult:
    y_true = np.asarray(y_true).astype(int)
    if y_prob is not None:
        y_prob = np.asarray(y_prob, dtype=float)
        y_pred = (y_prob >= threshold).astype(int)
    else:
        y_pred = np.asarray(y_pred).astype(int)
        y_prob = y_pred.astype(float)

    mb = compute_metrics(y_true, y_pred, y_prob, threshold)
    from sklearn.metrics import confusion_matrix as cm
    return EvalResult(
        name=name,
        metrics=mb,
        confusion=cm(y_true, y_pred, labels=[0, 1]),
        y_true=y_true,
        y_prob=y_prob,
        y_pred=y_pred,
        latency_ms=latency_ms,
        threshold=threshold,
        bootstrap=_bootstrap_report(y_true, y_prob),
    )


def _fix_confusion(result: EvalResult) -> EvalResult:
    from sklearn.metrics import confusion_matrix
    result.confusion = confusion_matrix(result.y_true, result.y_pred, labels=[0, 1])
    return result


@torch.no_grad()
def evaluate_gnn_graph(
    name: str,
    model: nn.Module,
    test_graphs: list[Data],
    device: torch.device,
    batch_size: int = 64,
    latency_ms: float | None = None,
    threshold: float = 0.5,
) -> EvalResult:
    y_true, y_prob = predict_graphs(model, test_graphs, device, batch_size)
    y_pred = (y_prob >= threshold).astype(int)
    mb = compute_metrics(y_true, y_pred, y_prob, threshold)
    r = EvalResult(
        name=name,
        metrics=mb,
        confusion=np.zeros((2, 2)),
        y_true=y_true,
        y_prob=y_prob,
        y_pred=y_pred,
        latency_ms=latency_ms,
        threshold=threshold,
        bootstrap=_bootstrap_report(y_true, y_prob),
    )
    return _fix_confusion(r)


def evaluate_flow_level_from_graphs(
    name: str,
    graphs: list[Data],
    y_prob_graph: np.ndarray,
    y_flow_true: np.ndarray,
    threshold: float = 0.5,
) -> EvalResult:
    from .graph_dataset import map_graph_preds_to_flows

    n = len(y_flow_true)
    flow_pred, flow_prob = map_graph_preds_to_flows(graphs, y_prob_graph, threshold, n)
    mask = flow_prob > 0
    if mask.sum() == 0:
        y_t, y_p = y_flow_true[:1], flow_prob[:1]
    else:
        y_t, y_p = y_flow_true[mask], flow_prob[mask]
    y_pr = (y_p >= threshold).astype(int)
    mb = compute_metrics(y_t, y_pr, y_p, threshold)
    r = EvalResult(
        name=name,
        metrics=mb,
        confusion=np.zeros((2, 2)),
        y_true=y_t,
        y_prob=y_p,
        y_pred=y_pr,
        threshold=threshold,
        bootstrap=_bootstrap_report(y_t, y_p),
    )
    return _fix_confusion(r)


def comparison_table(results: list[EvalResult]) -> str:
    header = (
        "| Model | Acc | Bal.Acc | Prec | Rec | Spec | F1 | MCC | ROC-AUC | PR-AUC | Latency |"
    )
    sep = "|-------|-----|---------|------|-----|------|-----|-----|---------|--------|---------|"
    lines = [header, sep]
    for r in results:
        m = r.metrics
        lat = f"{r.latency_ms:.2f}ms" if r.latency_ms is not None else "N/A"
        lines.append(
            f"| {r.name} | {m.accuracy:.4f} | {m.balanced_accuracy:.4f} | {m.precision:.4f} | "
            f"{m.recall:.4f} | {m.specificity:.4f} | {m.f1:.4f} | {m.mcc:.4f} | "
            f"{m.roc_auc:.4f} | {m.pr_auc:.4f} | {lat} |"
        )
    return "\n".join(lines)


def significance_table(
    y_true: np.ndarray,
    results: list[EvalResult],
    reference: str,
) -> str:
    ref = next((r for r in results if r.name == reference), results[0])
    lines = [f"### McNemar vs {reference}", "| Model | b | c | p-value | Significant |", "|-------|---|---|---------|-------------|"]
    for r in results:
        if r.name == reference:
            continue
        mc = mcnemar_test(y_true, ref.y_pred, r.y_pred)
        sig = "Yes" if mc["p_value"] < 0.05 else "No"
        lines.append(f"| {r.name} | {mc['b']} | {mc['c']} | {mc['p_value']:.4f} | {sig} |")
    return "\n".join(lines)


def log_report(result: EvalResult) -> None:
    m = result.metrics
    logger.info(
        "%s | acc=%.4f bal_acc=%.4f prec=%.4f rec=%.4f f1=%.4f mcc=%.4f roc=%.4f pr=%.4f",
        result.name, m.accuracy, m.balanced_accuracy, m.precision, m.recall,
        m.f1, m.mcc, m.roc_auc, m.pr_auc,
    )
    if result.bootstrap:
        f1b = result.bootstrap.get("f1", {})
        logger.info("  F1 bootstrap 95%% CI: [%.4f, %.4f]", f1b.get("ci_low", 0), f1b.get("ci_high", 0))


# Legacy
def evaluate_gnn(name, model, data, device, **kwargs):
    return evaluate_gnn_graph(name, model, [data], device, **kwargs)
