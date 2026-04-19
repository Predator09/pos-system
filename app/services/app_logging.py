from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.runtime_paths import get_data_dir

_LOGGER_NAME = "smartstock"


def _log_path() -> Path:
    p = get_data_dir() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p / "app.log"


def get_logger() -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(
        _log_path(),
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def log_exception(message: str, **context) -> None:
    logger = get_logger()
    suffix = ""
    if context:
        pairs = [f"{k}={context[k]!r}" for k in sorted(context)]
        suffix = " | " + ", ".join(pairs)
    logger.exception("%s%s", message, suffix)
