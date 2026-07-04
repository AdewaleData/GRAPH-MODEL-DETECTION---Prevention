"""Dataset loading utilities."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from .config import (
    BENIGN_LABEL,
    DATA_PATH,
    MAX_FLOWS,
    RANDOM_SEED,
    TARGET_COLUMN,
    TEST_RATIO,
    TRAIN_RATIO,
    VAL_RATIO,
)

logger = logging.getLogger(__name__)


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace and stray quotes from CSV headers."""
    df = df.copy()
    df.columns = df.columns.str.strip().str.strip("'")
    return df


def load_cic_ddos(path: Path | None = None) -> pd.DataFrame:
    """Load CICDDoS2019 CSV with standardized column names."""
    path = path or DATA_PATH
    logger.info("Loading dataset from %s", path)
    df = pd.read_csv(path)
    df = clean_column_names(df)
    logger.info("Loaded shape=%s", df.shape)
    return df


def stratified_sample(df: pd.DataFrame, max_rows: int = MAX_FLOWS) -> pd.DataFrame:
    """Down-sample while preserving label ratio — O(n) groupby sample."""
    if len(df) <= max_rows:
        logger.info("Using full dataset (%d rows)", len(df))
        return df.reset_index(drop=True)

    frac = max_rows / len(df)
    logger.info("Stratified sampling: %d -> ~%d rows (frac=%.4f)", len(df), max_rows, frac)
    sampled = (
        df.groupby(TARGET_COLUMN, group_keys=False)
        .apply(lambda g: g.sample(frac=min(1.0, frac * len(df) / len(g)), random_state=RANDOM_SEED))
        .reset_index(drop=True)
    )
    if len(sampled) > max_rows:
        sampled = sampled.sample(n=max_rows, random_state=RANDOM_SEED).reset_index(drop=True)
    logger.info("Sampled shape=%s", sampled.shape)
    return sampled


def binary_labels(series: pd.Series) -> np.ndarray:
    """Map labels to 0=BENIGN, 1=attack."""
    return (series != BENIGN_LABEL).astype(np.int64).values


def split_flows(
    X: np.ndarray,
    y: np.ndarray,
) -> tuple[np.ndarray, ...]:
    """Stratified train/val/test split for tabular models."""
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=(1 - TRAIN_RATIO), stratify=y, random_state=RANDOM_SEED
    )
    relative_test = TEST_RATIO / (VAL_RATIO + TEST_RATIO)
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=relative_test, stratify=y_temp, random_state=RANDOM_SEED
    )
    logger.info(
        "Split sizes train=%d val=%d test=%d",
        len(X_train),
        len(X_val),
        len(X_test),
    )
    return X_train, X_val, X_test, y_train, y_val, y_test
