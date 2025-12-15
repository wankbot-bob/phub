from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
from urllib.parse import urljoin

from app.client.phub import PornHub
from app.client.phub.constants import BASE_URL
from app.client.phub.parsers import parse_paging, parse_video_result
from app.client.phub.urls import UrlParser
from app.core.trailers import build_trailer_map
from app.core.utils import get_attr, get_soup, text_or_empty
from app.core.logging import verbose_print


def _enrich_videos_with_details(
    ph: PornHub,
    videos: list[dict],
    *,
    max_workers: int = 5,
    timeout: float = 10.0,
    total_timeout: float | None = None,
) -> list[dict]:
    """
    Fetch video detail pages to fill in preview, views, duration, and title.
    """
    def _enrich(video: dict) -> dict:
        url_or_id = video.get("url") or video.get("id")
        if not url_or_id:
            return video
        try:
            detail = ph.video(url_or_id)
            return {
                **video,
                "preview": detail.get("preview") or detail.get("thumb") or video.get("preview"),
                "views": detail.get("views") if detail.get("views") not in (None, 0) else video.get("views"),
                "duration": detail.get("duration") if detail.get("duration") not in (None, 0) else video.get("duration"),
                "title": detail.get("title") or video.get("title"),
            }
        except Exception:
            return video

    enriched: list[dict] = []
    total_timeout = total_timeout or (timeout * max(1, len(videos)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(_enrich, v): v for v in videos}
        for future in concurrent.futures.as_completed(future_map, timeout=total_timeout):
            try:
                enriched.append(future.result(timeout=timeout))
            except Exception:
                enriched.append(future_map[future])
    return enriched


def _attach_trailers_from_page(soup, videos: list[dict]) -> list[dict]:
    """
    Attach mediabook trailer URLs to videos on a channel page using data-video-vkey mapping.
    """
    trailer_map = build_trailer_map(soup)

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
    videos: list[dict] = []
    videos.extend(parse_video_result(soup, ".videoUList"))
    videos.extend(parse_video_result(soup, ".videos"))

    # Dedupe by URL/id to avoid double-counting when selectors overlap
    seen = set()
    unique_videos = []
    for v in videos:
        key = v.get("url") or v.get("id")
        if not key or key in seen:
            continue
        seen.add(key)
        unique_videos.append(v)
    if unique_videos:
        return unique_videos

    results = []
    for item in soup.select("li.pcVideoListItem"):
        link = item.select_one("a")
        if not link:
            continue
        url = urljoin(BASE_URL, get_attr(link, "href", ""))
        vid = UrlParser.get_video_id(url)
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


def _channel_page_url(input_url: str, page: int, *, gay: bool = False) -> str:
    """
    Build a channel videos URL from either a slug or full URL.

    We prefer the explicit /videos listing, which reliably exposes pagination.
    """
    if "://" in input_url:
        name = UrlParser.get_channel_name(input_url)
    else:
        name = input_url.strip("/")
    if not name:
        raise ValueError(f"Invalid channel input: {input_url}")

    prefix = "/channels"
    base = f"{BASE_URL}{prefix}/{name}/videos"
    if page > 1:
        return f"{base}?page={page}"
    return base


def collect_channel_videos(
    ph: PornHub,
    url: str,
    max_pages: int | None = None,
    *,
    enrich_details: bool = False,
    max_workers: int = 5,
    detail_timeout: float = 10.0,
    detail_total_timeout: float | None = None,
    verbose: bool = False,
) -> dict:
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
        verbose_print(verbose, f"[channel] fetch page {page_url}")
        res = ph.engine.request.get(page_url)
        soup = get_soup(res.text)

        page_videos = _parse_channel_videos(soup)
        page_videos = _attach_trailers_from_page(soup, page_videos)
        videos.extend(page_videos)

        paging = parse_paging(soup)

        if not page_videos:
            verbose_print(verbose, "[channel] stopping: empty page")
            break
        if max_pages is not None and page >= max_pages:
            verbose_print(verbose, "[channel] stopping: reached max-pages")
            break

        if paging.get("isEnd"):
            verbose_print(verbose, "[channel] stopping: paging isEnd")
            break

        max_page = paging.get("maxPage")
        if isinstance(max_page, int) and page >= max_page:
            verbose_print(verbose, "[channel] stopping: reached maxPage")
            break

        page += 1

    if enrich_details:
        videos = _enrich_videos_with_details(
            ph,
            videos,
            max_workers=max_workers,
            timeout=detail_timeout,
            total_timeout=detail_total_timeout,
        )
    return {"videos": videos, "paging": paging}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch channel videos from Pornhub.")
    parser.add_argument("url", nargs="?", help="Channel URL or slug (e.g., https://www.pornhub.com/channels/{name} or just name)")
    parser.add_argument("--max-pages", type=int, default=None, help="Limit how many pages to fetch.")
    parser.add_argument(
        "--enrich-details",
        action="store_true",
        help="Fetch each video page to fill preview/views/duration/title (slower, uses a thread pool).",
    )
    parser.add_argument("--workers", type=int, default=5, help="Worker threads for detail enrichment.")
    parser.add_argument("--detail-timeout", type=float, default=10.0, help="Per-video detail fetch timeout in seconds.")
    parser.add_argument("--detail-total-timeout", type=float, default=None, help="Overall timeout for detail enrichment.")
    parser.add_argument("--verbose", action="store_true", help="Log page fetching and loop stop reasons to stderr.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    ph = PornHub()
    result = collect_channel_videos(
        ph,
        args.url or "",
        max_pages=args.max_pages,
        enrich_details=bool(args.enrich_details),
        max_workers=args.workers,
        detail_timeout=args.detail_timeout,
        detail_total_timeout=args.detail_total_timeout,
        verbose=bool(args.verbose),
    )

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
