from __future__ import annotations

# Re-export Route/WebmasterRoute as shared route builders; site-specific clients can subclass/replace.
from app.client.phub.routes import Route, WebmasterRoute  # noqa: F401

__all__ = ["Route", "WebmasterRoute"]
