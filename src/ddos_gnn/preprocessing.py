"""Cleaning, encoding, and scaling."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler

from .config import DROP_COLUMNS, TARGET_COLUMN

logger = logging.getLogger(__name__)


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicates, handle infinities and missing values."""
    logger.info("Cleaning: initial rows=%d", len(df))
    df = df.drop_duplicates()
    df = df.replace([np.inf, -np.inf], np.nan)

    # Numeric coercion for object columns that should be numeric
    for col in df.columns:
        if col == TARGET_COLUMN:
            continue
        if df[col].dtype == object and col not in ("Source IP", "Destination IP", "Flow ID", "Timestamp"):
            df[col] = pd.to_numeric(df[col], errors="coerce")

    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        median = df[col].median()
        df[col] = df[col].fillna(median)

    if df[TARGET_COLUMN].isna().any():
        df = df.dropna(subset=[TARGET_COLUMN])

    logger.info("Cleaning: final rows=%d", len(df))
    return df.reset_index(drop=True)


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Domain-inspired flow features (vectorized array ops)."""
    df = df.copy()
    if "Total Fwd Packets" in df.columns and "Total Backward Packets" in df.columns:
        df["packet_ratio_fwd_bwd"] = df["Total Fwd Packets"] / (df["Total Backward Packets"] + 1)
    if "Flow Duration" in df.columns and "Flow Packets/s" in df.columns:
        df["duration_packet_rate"] = df["Flow Duration"] * df["Flow Packets/s"]
    if "SYN Flag Count" in df.columns and "ACK Flag Count" in df.columns:
        df["syn_ack_ratio"] = df["SYN Flag Count"] / (df["ACK Flag Count"] + 1)
    logger.info("Feature engineering complete; columns=%d", len(df.columns))
    return df


def get_feature_columns(df: pd.DataFrame) -> list[str]:
    """Columns used as model inputs."""
    exclude = set(DROP_COLUMNS)
    return [c for c in df.columns if c not in exclude and c != TARGET_COLUMN]


def prepare_tabular(
    df: pd.DataFrame,
    feature_cols: list[str] | None = None,
) -> tuple[np.ndarray, np.ndarray, list[str], RobustScaler]:
    """Build scaled X, binary y, and fitted scaler for deployment."""
    from .data_loader import binary_labels

    feature_cols = feature_cols or get_feature_columns(df)
    X = df[feature_cols].values.astype(np.float32)
    y = binary_labels(df[TARGET_COLUMN])

    scaler = RobustScaler()
    X = scaler.fit_transform(X).astype(np.float32)
    logger.info("Tabular matrix shape=%s", X.shape)
    return X, y, feature_cols, scaler
