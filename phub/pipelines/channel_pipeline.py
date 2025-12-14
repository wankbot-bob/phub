from __future__ import annotations

import argparse
import json
import sys
from urllib.parse import urljoin

from phub import PornHub
from phub.constants import BASE_URL
from phub.parsers import parse_paging, parse_video_result
from phub.urls import UrlParser
from phub.utils import get_attr, get_data, get_soup, text_or_empty


def _enrich_videos_with_details(ph: PornHub, videos: list[dict]) -> list[dict]:
    """
    Fetch video detail pages to fill in preview, views, duration, and title.
    """
    enriched = []
    for video in videos:
        url_or_id = video.get("url") or video.get("id")
        if not url_or_id:
            enriched.append(video)
            continue
        try:
            detail = ph.video(url_or_id)
            video = {
                **video,
                "preview": detail.get("preview") or detail.get("thumb") or video.get("preview"),
                "views": detail.get("views") if detail.get("views") not in (None, 0) else video.get("views"),
                "duration": detail.get("duration") if detail.get("duration") not in (None, 0) else video.get("duration"),
                "title": detail.get("title") or video.get("title"),
            }
        except Exception:
            pass
        enriched.append(video)
    return enriched


def _attach_trailers_from_page(soup, videos: list[dict]) -> list[dict]:
    """
    Attach mediabook trailer URLs to videos on a channel page using data-video-vkey mapping.
    """
    trailer_map: dict[str, str] = {}

    for li in soup.select("li[data-video-vkey]"):
        vkey = li.get("data-video-vkey")
        if not vkey:
            continue
        node = li.select_one("[data-mediabook]")
        if node:
            trailer = get_attr(node, "data-mediabook", "") or get_data(node, "mediabook", "")
            if trailer:
                trailer_map[vkey] = trailer

    if not trailer_map:
        for node in soup.select("a[href*='view_video.php?viewkey='] [data-mediabook]"):
            parent_link = node.find_parent("a")
            if not parent_link:
                continue
            href = get_attr(parent_link, "href", "")
            vkey = UrlParser.get_video_id(href)
            trailer = get_attr(node, "data-mediabook", "") or get_data(node, "mediabook", "")
            if vkey and trailer:
                trailer_map[vkey] = trailer

    enriched = []
    for video in videos:
        vkey = UrlParser.get_video_id(video.get("url") or video.get("id") or "")
        trailer = trailer_map.get(vkey)
        if trailer:
            video = {**video, "trailer": trailer}
        enriched.append(video)
    return enriched


def _parse_channel_videos(soup) -> list[dict]:
    """
    Try multiple selectors to extract channel videos.
    """
    videos = parse_video_result(soup, ".videoUList")
    if videos:
        return videos

    results = []
    for item in soup.select("li.pcVideoListItem"):
        link = item.select_one("a")
        if not link:
            continue
        url = urljoin(BASE_URL, get_attr(link, "href", ""))
        vid = UrlParser.getVideoID(url)
        img = item.select_one("img")
        preview = (
            get_attr(img, "data-thumb_url", "")
            or get_attr(img, "data-src", "")
            or get_attr(img, "src", "")
        )
        duration = text_or_empty(item.select_one(".duration"))
        views = text_or_empty(item.select_one(".views var")) or text_or_empty(item.select_one(".views"))
        results.append(
            {
                "title": get_attr(link, "title", "") or text_or_empty(item.select_one(".title")),
                "id": vid,
                "url": url,
                "views": views,
                "duration": duration,
                "hd": bool(item.select_one(".hd-thumbnail")),
                "premium": bool(item.select_one(".premiumIcon")),
                "freePremium": bool(item.select_one(".marker-overlays .phpFreeBlock")),
                "preview": preview,
            }
        )
    return results


def _channel_page_url(input_url: str, page: int) -> str:
    name = UrlParser.get_channel_name(input_url)
    if not name:
        raise ValueError(f"Invalid channel URL: {input_url}")
    base = f"{BASE_URL}/channels/{name}"
    if page > 1:
        return f"{base}?page={page}"
    return base


def collect_channel_videos(ph: PornHub, url: str, max_pages: int | None = None) -> dict:
    """
    Fetch videos from a channel, respecting a page limit if provided.
    """
    videos: list[dict] = []
    page = 1
    paging = None
    # Warm up cookies to avoid deterrence redirects
    try:
        ph.engine.request.get(BASE_URL + "/")
    except Exception:
        pass

    while True:
        page_url = _channel_page_url(url, page)
        res = ph.engine.request.get(page_url)
        soup = get_soup(res.text)

        page_videos = _parse_channel_videos(soup)
        page_videos = _attach_trailers_from_page(soup, page_videos)
        videos.extend(page_videos)

        paging = parse_paging(soup)

        if max_pages is not None and page >= max_pages:
            break

        if paging.get("isEnd"):
            break

        if paging.get("maxPage") and page >= paging.get("maxPage"):
            break

        page += 1

    videos = _enrich_videos_with_details(ph, videos)
    return {"videos": videos, "paging": paging}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch channel videos from Pornhub.")
    parser.add_argument("url", help="Channel URL (https://www.pornhub.com/channels/{name})")
    parser.add_argument("--max-pages", type=int, default=None, help="Limit how many pages to fetch.")
    args = parser.parse_args(argv)

    ph = PornHub()
    result = collect_channel_videos(ph, args.url, max_pages=args.max_pages)

    payload = {
        "input": args.url,
        "videos": result["videos"],
        "paging": result.get("paging"),
    }
    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False, default=str)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
