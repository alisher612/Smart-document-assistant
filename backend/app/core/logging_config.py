
import logging
from logging.config import dictConfig

from app.core.config import settings


def setup_logging():

    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,

        "formatters": {
            "default": {
                "format": (
                    "%(asctime)s | "
                    "%(levelname)s | "
                    "%(name)s | "
                    "%(message)s"
                )
            }
        },

        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "level": settings.LOG_LEVEL,
            }
        },

        "root": {
            "handlers": ["console"],
            "level": settings.LOG_LEVEL,
        },
    })


logger = logging.getLogger("smart_document_assistant")
