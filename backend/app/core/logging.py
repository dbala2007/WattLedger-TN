"""Central logging setup.

CLAUDE.md asks for logger usage instead of print() everywhere. This module
configures the root logger once, and get_logger() hands out named loggers
(e.g. "app.services.reading_service") so log lines show which module they
came from.
"""

import logging

from app.core.config import settings

_configured = False


def configure_logging() -> None:
    """Set up the root logger's format and level. Safe to call more than once."""
    global _configured
    if _configured:
        return

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger, e.g. get_logger(__name__)."""
    configure_logging()
    return logging.getLogger(name)
