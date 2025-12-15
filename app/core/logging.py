import sys


def verbose_print(enabled: bool, message: str) -> None:
    """Print to stderr when verbose is enabled."""
    if enabled:
        print(message, file=sys.stderr)


__all__ = ["verbose_print"]
