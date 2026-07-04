"""Plotly and Matplotlib visualization helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
from sklearn.metrics import auc, precision_recall_curve, roc_curve


def plot_label_distribution(df: pd.DataFrame, label_col: str, save_path: Path | None = None) -> go.Figure:
    counts = df[label_col].value_counts().reset_index()
    counts.columns = ["Label", "Count"]
    fig = px.bar(counts, x="Label", y="Count", title="Traffic Label Distribution", color="Label")
    fig.update_layout(showlegend=False)
    if save_path:
        fig.write_html(str(save_path))
    return fig


def plot_correlation_heatmap(X: np.ndarray, feature_names: list[str], top_k: int = 25, save_path: Path | None = None):
    k = min(top_k, X.shape[1])
    idx = np.argsort(np.var(X, axis=0))[-k:]
    corr = np.corrcoef(X[:, idx], rowvar=False)
    names = [feature_names[i][:30] for i in idx]
    fig, ax = plt.subplots(figsize=(12, 10))
    sns.heatmap(corr, xticklabels=names, yticklabels=names, cmap="viridis", ax=ax)
    ax.set_title("Feature Correlation Heatmap (Top Variance Features)")
    plt.xticks(rotation=90)
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
    return fig


def plot_training_curves(history: dict[str, list[float]], title: str, save_path: Path | None = None) -> go.Figure:
    fig = go.Figure()
    epochs = list(range(1, len(history.get("train_loss", [])) + 1))
    if "train_loss" in history:
        fig.add_trace(go.Scatter(x=epochs, y=history["train_loss"], name="Train Loss"))
    if "val_loss" in history:
        fig.add_trace(go.Scatter(x=epochs, y=history["val_loss"], name="Val Loss"))
    fig.update_layout(title=title, xaxis_title="Epoch", yaxis_title="Loss")
    if save_path:
        fig.write_html(str(save_path))
    return fig


def plot_confusion_matrix(cm: np.ndarray, title: str, save_path: Path | None = None):
    fig, ax = plt.subplots(figsize=(5, 4))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax, xticklabels=["Benign", "DDoS"], yticklabels=["Benign", "DDoS"])
    ax.set_title(title)
    ax.set_ylabel("True")
    ax.set_xlabel("Predicted")
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
    return fig


def plot_roc_curve(y_true: np.ndarray, y_prob: np.ndarray, title: str, save_path: Path | None = None):
    fpr, tpr, _ = roc_curve(y_true, y_prob)
    roc_auc = auc(fpr, tpr)
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(fpr, tpr, label=f"AUC = {roc_auc:.4f}")
    ax.plot([0, 1], [0, 1], "k--", alpha=0.4)
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title(title)
    ax.legend()
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
    return fig


def plot_pr_curve(y_true: np.ndarray, y_prob: np.ndarray, title: str, save_path: Path | None = None):
    precision, recall, _ = precision_recall_curve(y_true, y_prob)
    ap = auc(recall, precision)
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(recall, precision, label=f"AP = {ap:.4f}")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title(title)
    ax.legend()
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
    return fig


def plot_feature_importance(importances: np.ndarray, names: list[str], top_k: int = 20, save_path: Path | None = None):
    idx = np.argsort(importances)[-top_k:]
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh([names[i][:35] for i in idx], importances[idx], color="#6366f1")
    ax.set_title("Feature Importance (Random Forest)")
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
    return fig


def plot_graph_network(
    G: nx.DiGraph,
    node_labels: dict[int, int] | None = None,
    title: str = "Network Communication Graph",
    save_path: Path | None = None,
):
    """Visualize graph; attack nodes highlighted in red."""
    pos = nx.spring_layout(G, seed=42)
    colors = []
    for n in G.nodes():
        if node_labels and node_labels.get(n, 0) == 1:
            colors.append("#ef4444")
        else:
            colors.append("#22c55e")

    fig, ax = plt.subplots(figsize=(10, 8))
    nx.draw_networkx_edges(G, pos, ax=ax, alpha=0.3, arrows=True, arrowsize=8)
    nx.draw_networkx_nodes(G, pos, node_color=colors, node_size=120, ax=ax)
    ax.set_title(title)
    ax.axis("off")
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
    return fig


def plot_realtime_attack_highlight(G: nx.DiGraph, attack_nodes: list[int], save_path: Path | None = None):
    """Highlight nodes discovered via DFS/BFS attack region traversal."""
    pos = nx.spring_layout(G, seed=42)
    node_colors = ["#ef4444" if n in attack_nodes else "#94a3b8" for n in G.nodes()]
    fig, ax = plt.subplots(figsize=(10, 8))
    nx.draw_networkx_edges(G, pos, ax=ax, alpha=0.2)
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=150, ax=ax)
    ax.set_title("Real-Time Attack Region (DFS-highlighted nodes)")
    ax.axis("off")
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
    return fig
