"""Structured logging configuration."""

import logging
import sys
from pathlib import Path

from .config import DB_DIR


def setup_logging(level: int = logging.INFO) -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    log_path = DB_DIR / "api.log"

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    root.addHandler(console)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.info("Logging initialized -> %s", log_path)
