from __future__ import annotations

from typing import Any, Dict, List
from urllib.parse import urljoin

from app.client.rtube.constants import BASE_URL
from app.client.rtube.urls import UrlParser
from app.core.utils import get_attr, get_data, get_soup, text_or_empty


def parse_video_list(html: str) -> List[Dict[str, Any]]:
    soup = get_soup(html)
    items = []
    for card in soup.select("li.video-item, div.video-item, div.video"):
        link = card.select_one("a[href]")
        if not link:
            continue
        href = get_attr(link, "href", "")
        url = urljoin(BASE_URL, href)
        vid = UrlParser.get_video_id(url)
        img = card.select_one("img") or link.select_one("img")
        preview = get_attr(img, "src", "") or get_attr(img, "data-thumb", "") or get_attr(img, "data-src", "")
        duration = text_or_empty(card.select_one(".duration, .video-duration"))
        views = text_or_empty(card.select_one(".views, .video-views"))
        title = get_attr(link, "title", "") or text_or_empty(link) or text_or_empty(card.select_one(".video-title"))
        items.append(
            {
                "title": title,
                "id": vid,
                "url": url,
                "views": views,
                "duration": duration,
                "preview": preview,
            }
        )
    return items


def parse_performer_profile(html: str) -> Dict[str, Any]:
    soup = get_soup(html)
    name = text_or_empty(soup.select_one("h1, .title, .profile-title"))
    avatar = get_attr(soup.select_one("img.avatar, img.profile-image"), "src", "")
    bio = text_or_empty(soup.select_one(".bio, .description"))
    return {"name": name, "avatar": avatar, "bio": bio}
