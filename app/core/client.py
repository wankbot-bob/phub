from __future__ import annotations

from app.core.engine import Engine


class BaseClient:
    """
    Minimal shared client wrapper for site-specific clients.
    """

    def __init__(self, engine: Engine | None = None):
        self.engine = engine or Engine()


__all__ = ["BaseClient"]
