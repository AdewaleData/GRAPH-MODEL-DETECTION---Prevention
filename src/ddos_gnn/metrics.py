"""Extended metrics, bootstrap CIs, and statistical significance tests."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

import numpy as np
from scipy import stats
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)

logger = logging.getLogger(__name__)


@dataclass
class MetricBundle:
    """Comprehensive classification metrics for security reporting."""

    accuracy: float = 0.0
    balanced_accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    specificity: float = 0.0
    f1: float = 0.0
    mcc: float = 0.0
    fpr: float = 0.0
    fnr: float = 0.0
    roc_auc: float = 0.0
    pr_auc: float = 0.0
    brier: float = 0.0
    support_positive: int = 0
    support_negative: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: np.ndarray | None = None,
    threshold: float = 0.5,
) -> MetricBundle:
    """Compute full metric bundle; y_prob optional for probabilistic scores."""
    y_true = np.asarray(y_true).astype(int)
    if y_prob is not None:
        y_prob = np.asarray(y_prob, dtype=float)
        y_pred = (y_prob >= threshold).astype(int)
    else:
        y_pred = np.asarray(y_pred).astype(int)

    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    fnr = fn / (fn + tp) if (fn + tp) else 0.0

    prob = y_prob if y_prob is not None else y_pred.astype(float)
    roc = roc_auc_score(y_true, prob) if len(np.unique(y_true)) > 1 else 0.0
    pr_auc = average_precision_score(y_true, prob) if len(np.unique(y_true)) > 1 else 0.0
    brier = brier_score_loss(y_true, np.clip(prob, 1e-6, 1 - 1e-6)) if y_prob is not None else 0.0

    return MetricBundle(
        accuracy=float(accuracy_score(y_true, y_pred)),
        balanced_accuracy=float(balanced_accuracy_score(y_true, y_pred)),
        precision=float(precision_score(y_true, y_pred, zero_division=0)),
        recall=float(recall_score(y_true, y_pred, zero_division=0)),
        specificity=float(specificity),
        f1=float(f1_score(y_true, y_pred, zero_division=0)),
        mcc=float(matthews_corrcoef(y_true, y_pred)) if len(np.unique(y_true)) > 1 else 0.0,
        fpr=float(fpr),
        fnr=float(fnr),
        roc_auc=float(roc),
        pr_auc=float(pr_auc),
        brier=float(brier),
        support_positive=int((y_true == 1).sum()),
        support_negative=int((y_true == 0).sum()),
    )


def find_best_threshold(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    metric: str = "f1",
) -> tuple[float, float]:
    """Grid-search threshold on validation probabilities."""
    y_true = np.asarray(y_true).astype(int)
    y_prob = np.asarray(y_prob, dtype=float)
    best_t, best_score = 0.5, -1.0
    for t in np.linspace(0.05, 0.95, 91):
        pred = (y_prob >= t).astype(int)
        if metric == "f1":
            score = f1_score(y_true, pred, zero_division=0)
        elif metric == "balanced_accuracy":
            score = balanced_accuracy_score(y_true, pred)
        elif metric == "mcc":
            score = matthews_corrcoef(y_true, pred) if len(np.unique(pred)) > 1 else 0.0
        else:
            score = f1_score(y_true, pred, zero_division=0)
        if score > best_score:
            best_score, best_t = score, float(t)
    logger.info("Best threshold=%.3f (%s=%.4f)", best_t, metric, best_score)
    return best_t, best_score


def bootstrap_ci(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    metric_fn: Callable[[np.ndarray, np.ndarray], float],
    n_bootstrap: int = 1000,
    alpha: float = 0.05,
    seed: int = 42,
) -> tuple[float, float, float]:
    """Bootstrap 95% CI: returns (point_estimate, lower, upper)."""
    rng = np.random.default_rng(seed)
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    n = len(y_true)
    point = metric_fn(y_true, y_prob)
    if n < 10:
        return point, point, point

    scores = []
    for _ in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        yt, yp = y_true[idx], y_prob[idx]
        if len(np.unique(yt)) < 2:
            continue
        try:
            scores.append(metric_fn(yt, yp))
        except ValueError:
            continue

    if not scores:
        return point, point, point
    lo = float(np.percentile(scores, 100 * alpha / 2))
    hi = float(np.percentile(scores, 100 * (1 - alpha / 2)))
    return float(point), lo, hi


def mcnemar_test(y_true: np.ndarray, pred_a: np.ndarray, pred_b: np.ndarray) -> dict[str, float]:
    """McNemar test for paired classifier comparison (same test set)."""
    y_true = np.asarray(y_true).astype(int)
    pred_a = np.asarray(pred_a).astype(int)
    pred_b = np.asarray(pred_b).astype(int)
    correct_a = pred_a == y_true
    correct_b = pred_b == y_true
    b = int(np.sum(correct_a & ~correct_b))  # A right, B wrong
    c = int(np.sum(~correct_a & correct_b))  # A wrong, B right
    if b + c == 0:
        return {"statistic": 0.0, "p_value": 1.0, "b": b, "c": c}
    # Exact two-sided binomial test on discordant pairs (b vs c)
    n = b + c
    k = min(b, c)
    p_value = float(2 * stats.binom.cdf(k, n, 0.5))
    p_value = min(p_value, 1.0)
    return {"statistic": float(n), "p_value": p_value, "b": b, "c": c}


def seed_aggregate(
    metric_dicts: list[dict[str, float]],
    metric_keys: list[str] | None = None,
) -> dict[str, dict[str, float]]:
    """Mean ± std across seeds; paired t-test vs first model if multiple series."""
    if not metric_dicts:
        return {}
    keys = metric_keys or [k for k in metric_dicts[0] if isinstance(metric_dicts[0][k], (int, float))]
    out: dict[str, dict[str, float]] = {}
    for k in keys:
        vals = [float(d[k]) for d in metric_dicts if k in d]
        if not vals:
            continue
        out[k] = {
            "mean": float(np.mean(vals)),
            "std": float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0,
            "n": len(vals),
        }
    return out


def compare_seeds_paired(
    metric_a: list[float],
    metric_b: list[float],
) -> dict[str, float]:
    """Paired t-test on same-metric values across matched seeds."""
    a = np.asarray(metric_a, dtype=float)
    b = np.asarray(metric_b, dtype=float)
    if len(a) != len(b) or len(a) < 2:
        return {"t_statistic": 0.0, "p_value": 1.0}
    t, p = stats.ttest_rel(a, b)
    return {"t_statistic": float(t), "p_value": float(p)}
