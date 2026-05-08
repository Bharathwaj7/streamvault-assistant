import logging
import logging.handlers
import sys
from pathlib import Path
from pythonjsonlogger import jsonlogger
from app.core.config import get_settings


def setup_logging() -> logging.Logger:
    settings = get_settings()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Create logs directory
    log_dir = Path("/app/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("streamvault")
    logger.setLevel(log_level)

    # ── JSON formatter ────────────────────────────────────────────────────────
    json_fmt = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # ── Console handler ───────────────────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(json_fmt)

    # ── Rotating file handler ─────────────────────────────────────────────────
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "streamvault.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(json_fmt)

    # ── Error file handler ────────────────────────────────────────────────────
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "errors.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(json_fmt)

    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        logger.addHandler(error_handler)

    return logger


def get_logger(name: str = "streamvault") -> logging.Logger:
    return logging.getLogger(name)
