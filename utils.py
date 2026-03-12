"""Utility helpers: logging setup and simple helpers."""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(log_path: str = "valtrilabs.log") -> logging.Logger:
    logger = logging.getLogger("valtrilabs")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        fh = RotatingFileHandler(log_path, maxBytes=5_000_000, backupCount=3)
        fh.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        fh.setFormatter(fmt)
        ch.setFormatter(fmt)
        logger.addHandler(fh)
        logger.addHandler(ch)
    return logger


def ensure_data_dirs(base: str = "data") -> None:
    Path(base).mkdir(exist_ok=True)
    Path(f"{base}/pdfs").mkdir(parents=True, exist_ok=True)
