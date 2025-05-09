import logging
import logging.config
from typing import Any, Dict

from core.config import get_settings


def setup_logging() -> None:
    """Set up logging configuration."""
    settings = get_settings()
    level = "DEBUG" if settings.debug else "INFO"

    LOGGING: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "level": level,
                "stream": "ext://sys.stdout",
            },
            # "file": {
            #     "class": "logging.handlers.RotatingFileHandler",
            #     "formatter": "default",
            #     "level": level,
            #     "filename": "logs/app.log",
            #     "maxBytes": 10 * 1024 * 1024,
            #     "backupCount": 5,
            #     "encoding": "utf-8",
            # },
        },
        "loggers": {
            "": {  # root logger
                # "handlers": ["console", "file"],
                "handlers": ["console"],
                "level": level,
                "propagate": True,
            },
            "uvicorn.error": {"level": level},
            "uvicorn.access": {"handlers": ["console"], "level": "INFO", "propagate": False},
        },
    }

    logging.config.dictConfig(LOGGING)
