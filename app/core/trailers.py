from __future__ import annotations

from typing import Dict

from .utils import get_attr, get_data


def _extract_viewkey(href: str) -> str:
    if "viewkey=" in href:
        return href.split("viewkey=", 1)[1].split("&", 1)[0]
    # fallback: try to take last path segment
    parts = href.rstrip("/").split("/")
    return parts[-1] if parts else href


def build_trailer_map(soup) -> Dict[str, str]:
    """
    Build a map of viewkey -> mediabook trailer URL from a soup document.
    Prefers explicit data-video-vkey carriers, falls back to links with viewkey.
    """
    trailer_map: Dict[str, str] = {}

    for li in soup.select("li[data-video-vkey]"):
        vkey = get_attr(li, "data-video-vkey", "")
        if not vkey:
            continue
        node = li.select_one("[data-mediabook]")
        trailer = get_attr(node, "data-mediabook", "") or get_data(node, "mediabook", "") if node else ""
        if trailer:
            trailer_map[vkey] = trailer

    for node in soup.select("a[href*='view_video.php?viewkey='] [data-mediabook]"):
        parent_link = node.find_parent("a")
        if not parent_link:
            continue
        href = get_attr(parent_link, "href", "")
        vkey = _extract_viewkey(href)
        trailer = get_attr(node, "data-mediabook", "") or get_data(node, "mediabook", "")
        if vkey and trailer and vkey not in trailer_map:
            trailer_map[vkey] = trailer

    return trailer_map
