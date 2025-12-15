class HttpStatusError(Exception):
    """Raised when a non-2xx HTTP status is returned."""


class IllegalError(Exception):
    """Raised when Pornhub returns a deterrence/illegal warning page."""
