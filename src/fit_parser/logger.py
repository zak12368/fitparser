"""Logging configuration for the FIT parser.

Usage:
    from fit_parser.logger import get_logger
    logger = get_logger(__name__)
"""

import logging
import sys
from typing import Final

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOG_LEVEL: Final = logging.DEBUG
_LOG_FORMAT: Final = "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s"
_DATE_FORMAT: Final = "%H:%M:%S"

# ---------------------------------------------------------------------------
# Logger factory
# ---------------------------------------------------------------------------


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger for the given module name."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT))
        logger.addHandler(handler)

    logger.setLevel(_LOG_LEVEL)
    return logger
