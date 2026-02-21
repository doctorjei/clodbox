"""Logging setup for kanibako."""

from __future__ import annotations

import logging
import sys


def setup_logging(verbose: bool = False) -> None:
    """Configure the ``kanibako`` root logger.

    Normal mode: WARNING+ to stderr.
    Verbose mode: DEBUG+ to stderr with ``kanibako: <message>`` format.
    """
    logger = logging.getLogger("kanibako")
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stderr)
    if verbose:
        logger.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter("kanibako: %(message)s"))
    else:
        logger.setLevel(logging.WARNING)

    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under ``kanibako``."""
    return logging.getLogger(f"kanibako.{name}")
