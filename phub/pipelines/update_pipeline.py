from __future__ import annotations

import argparse
import json
import sys
from urllib.parse import urlparse

from phub import PornHub
from phub.constants import BASE_URL
from phub.urls import UrlParser
from phub.utils import get_attr, get_data, get_soup, text_or_empty


def detect_kind(url: str) -> str:
    path = urlparse(url).path.lower()
    if "/model/" in path:
        return "model"
    if "/pornstar/" in path:
        return "pornstar"
    raise ValueError("URL must contain /model/ or /pornstar/")


def stream_url(kind: str, name: str, page: int | None = None) -> str:
    base = f"{BASE_URL}/{kind}/{name}/stream"
    suffix = "?section=videos&display=owner"
    if page and page > 1:
        suffix += f"&page={page}"
    return base + suffix


def parse_stream_videos(html: str) -> list[dict]:
    soup = get_soup(html)
    videos: list[dict] = []

    for li in soup.select("li.pcVideoListItem[data-video-vkey]"):
        vkey = li.get("data-video-vkey")
        link = li.select_one("a[href*='view_video.php']")
        url = ""
        if link:
            href = get_attr(link, "href", "")
            url = BASE_URL + href if href.startswith("/") else href
        title = text_or_empty(link)
        img = li.select_one("img[data-mediabook]")
        preview = (
            get_attr(img, "src", "")
            or get_attr(img, "data-mediumthumb", "")
            or get_attr(img, "data-image", "")
        )
        trailer = get_attr(img, "data-mediabook", "") or get_data(img, "mediabook", "")
        duration = text_or_empty(li.select_one(".duration"))
        views = text_or_empty(li.select_one(".views var")) or text_or_empty(li.select_one(".views"))
        videos.append(
            {
                "title": title,
                "id": vkey or UrlParser.get_video_id(url),
                "url": url,
                "views": views,
                "duration": duration,
                "hd": bool(li.select_one(".hd-thumbnail")),
                "premium": bool(li.select_one(".premiumIcon")),
                "freePremium": bool(li.select_one(".marker-overlays .phpFreeBlock")),
                "preview": preview,
                **({"trailer": trailer} if trailer else {}),
            }
        )
    return videos


def collect_stream_videos(ph: PornHub, url: str, max_pages: int | None = None) -> list[dict]:
    kind = detect_kind(url)
    name = UrlParser.get_model_name(url) if kind == "model" else UrlParser.get_pornstar_name(url)
    all_videos: list[dict] = []
    page = 1
    while True:
        target = stream_url(kind, name, page)
        try:
            res = ph.engine.request.get(target)
        except Exception:
            break
        page_videos = parse_stream_videos(res.text)
        if not page_videos:
            break
        all_videos.extend(page_videos)
        if max_pages is not None and page >= max_pages:
            break
        page += 1
    return all_videos


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch performer stream (owner videos) feed and extract video entries.")
    parser.add_argument("url", help="Performer URL (https://www.pornhub.com/model/{name} or /pornstar/{name})")
    parser.add_argument("--max-pages", type=int, default=None, help="Limit number of stream pages to fetch.")
    args = parser.parse_args(argv)

    ph = PornHub()
    videos = collect_stream_videos(ph, args.url, max_pages=args.max_pages)

    payload = {
        "input": args.url,
        "videos": videos,
    }
    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False, default=str)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
