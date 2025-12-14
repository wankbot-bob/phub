from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable, Optional

from bs4 import BeautifulSoup
from bs4.element import Tag


def get_soup(html: str) -> BeautifulSoup:
    """Parse HTML into a BeautifulSoup document."""
    return BeautifulSoup(html, "lxml")


def get_attr(el: Optional[Tag], name: str, default: Any = None) -> Any:
    if el is None:
        return default
    return el.attrs.get(name, default)


def get_data(el: Optional[Tag], name: str, default: Any = None) -> Any:
    """Get a data-* attribute with graceful fallback."""
    if el is None:
        return default
    return el.attrs.get(f"data-{name}", el.attrs.get(name, default))


def text_or_empty(el: Optional[Tag]) -> str:
    return (el.get_text() if el else "").strip()


def parse_readable_number(value: str) -> int:
    """Parse strings like '14M', '1,204', '12K' into an integer."""
    if not value:
        return 0
    cleaned = value.replace(",", "").strip()
    multiplier = 1
    if cleaned.endswith("K"):
        multiplier = 1_000
        cleaned = cleaned[:-1]
    elif cleaned.endswith("M"):
        multiplier = 1_000_000
        cleaned = cleaned[:-1]
    elif cleaned.endswith("B"):
        multiplier = 1_000_000_000
        cleaned = cleaned[:-1]
    try:
        return int(float(cleaned) * multiplier)
    except (TypeError, ValueError):
        return 0


def to_hhmmss(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds // 60) % 60
    secs = seconds % 60
    parts = [hours, minutes, secs]
    formatted = [f"{p:02d}" for p in parts]
    while formatted and formatted[0] == "00" and len(formatted) > 2:
        formatted.pop(0)
    return ":".join(formatted) or "00:00"


def searchify(keyword: str) -> str:
    """
    Transform a string into a search keyword used by Pornhub's search fields.
    Mirrors the behavior of the original JS helper.
    """
    replacements = {
        r"[ \t]+$|^[ \t]+": " ",
        r"[\\.,'/:=\(\)&!\?@\[\]\"*\$#%\^;\|`~><¿\{\}\+]": " ",
        "【|】|〈|〉|〖|〗|（|）|　|〔|〕|『|』|］|［": "",
    }
    lowered = keyword
    for pattern, repl in replacements.items():
        lowered = re.sub(pattern, repl, lowered)

    lowered = lowered.replace("é", "e").replace("è", "e").replace("ë", "e").replace("ê", "e")
    lowered = lowered.replace("ä", "a").replace("à", "a").replace("â", "a")
    lowered = lowered.replace("ü", "u").replace("ù", "u").replace("û", "u")
    lowered = lowered.replace("î", "i").replace("ï", "i").replace("ô", "o").replace("ç", "c")
    lowered = unicodedata.normalize("NFKC", lowered)
    lowered = " ".join(lowered.strip().split())
    return lowered.replace(" ", "+")


def dashify(keywords: str | Iterable[str]) -> str:
    if isinstance(keywords, str):
        return keywords.strip()
    return "-".join(sorted([k.strip() for k in keywords if k.strip()]))


def slugify(keyword: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", keyword)
    return "-".join(cleaned.strip().split())


def remove_comma(value: str) -> str:
    return value.replace(",", "")


def remove_protection_bracket(value: str) -> str:
    return re.sub(r"\(.+?\)", "", value)


def unescape(value: str) -> Optional[str]:
    if not isinstance(value, str):
        return None
    return (
        value.replace("\\", "")
        .replace("%2C", ",")
        .replace("%5B", "[")
        .replace("%5D", "]")
        .replace("&amp;", "&")
    )
