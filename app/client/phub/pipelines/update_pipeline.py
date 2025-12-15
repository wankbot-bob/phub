from __future__ import annotations

import argparse
import json
import sys
import math
from urllib.parse import urlparse

from app.client.phub import PornHub
from app.client.phub.constants import BASE_URL
from app.client.phub.parsers import parse_counting, parse_paging, parse_video_result
from app.core.trailers import build_trailer_map
from app.client.phub.urls import UrlParser
from app.core.utils import get_attr, get_data, get_soup, slugify, text_or_empty
from app.client.phub.pipelines.performer_pipeline import _fallback_videos


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
    trailer_map = build_trailer_map(soup)
    videos: list[dict] = []

    for li in soup.select("li.pcVideoListItem[data-video-vkey]"):
        vkey = li.get("data-video-vkey")
        link = li.select_one("a[href*='view_video.php']")
        url = ""
        if link:
            href = get_attr(link, "href", "")
            url = BASE_URL + href if href.startswith("/") else href
        title = text_or_empty(link)
        img = li.select_one("img[data-mediabook], img")
        preview = (
            get_attr(img, "src", "")
            or get_attr(img, "data-mediumthumb", "")
            or get_attr(img, "data-image", "")
        )
        trailer = trailer_map.get(vkey or UrlParser.get_video_id(url))
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


def collect_stream_videos(ph: PornHub, url: str, max_pages: int | None = None, *, verbose: bool = False) -> tuple[list[dict], list[str]]:
    kind = detect_kind(url)
    name = UrlParser.get_model_name(url) if kind == "model" else UrlParser.get_pornstar_name(url)
    all_videos: list[dict] = []
    warnings: list[str] = []
    page = 1
    while True:
        target = stream_url(kind, name, page)
        try:
            res = ph.engine.request.get(target)
        except Exception as exc:
            warnings.append(f"stream fetch failed: {exc}")
            break
        if verbose:
            print(f"[update] fetch stream page {target}", file=sys.stderr)
        page_videos = parse_stream_videos(res.text)
        if not page_videos:
            break
        all_videos.extend(page_videos)
        if max_pages is not None and page >= max_pages:
            break
        page += 1
    if not all_videos and kind == "model":
        # Fallback: scrape model uploaded videos pages directly.
        base_path = f"{BASE_URL}/model/{name}/videos"
        page = 1
        scraped: list[dict] = []
        while True:
            try:
                page_url = base_path if page == 1 else f"{base_path}?page={page}"
                res = ph.engine.request.get(page_url)
                soup = get_soup(res.text)
            except Exception as exc:
                warnings.append(f"model videos fetch failed: {exc}")
                break
            if verbose:
                print(f"[update] fetch model videos page {page_url}", file=sys.stderr)
            page_items = parse_video_result(soup, ".videoUList") or parse_video_result(soup, "li.videoblock")
            trailer_map = build_trailer_map(soup)
            enriched = []
            for item in page_items:
                vkey = UrlParser.get_video_id(item.get("url") or item.get("id") or "")
                trailer = trailer_map.get(vkey)
                if trailer:
                    item = {**item, "trailer": trailer}
                enriched.append(item)
            scraped.extend(enriched)

            paging = parse_paging(soup)
            counting_info = parse_counting(soup)
            max_page = paging.get("maxPage")
            if not page_items:
                break
            if paging.get("isEnd") or (isinstance(max_page, int) and page >= max_page):
                break
            if max_pages is not None and page >= max_pages:
                break
            if counting_info["total"] and counting_info["to"] >= counting_info["from"]:
                per_page = counting_info["to"] - counting_info["from"] + 1
                if per_page > 0:
                    pages_total = math.ceil(counting_info["total"] / per_page)
                    if page >= pages_total:
                        break
            if page >= 20:  # safety cap
                break
            page += 1
        if scraped:
            all_videos = scraped
        else:
            fallback_videos, _, _ = _fallback_videos(ph, url)
            if not fallback_videos:
                warnings.append("model videos fallback returned no items")
            all_videos = fallback_videos
    return all_videos, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch performer stream (owner videos) feed and extract video entries.")
    parser.add_argument("url", nargs="?", help="Performer URL (https://www.pornhub.com/model/{name} or /pornstar/{name})")
    parser.add_argument("--pornstar", help="Pornstar slug (shortcut for https://www.pornhub.com/pornstar/{name})")
    parser.add_argument("--model", help="Model slug (shortcut for https://www.pornhub.com/model/{name})")
    parser.add_argument("--max-pages", type=int, default=None, help="Limit number of stream pages to fetch (also applied to fallback scraping).")
    parser.add_argument("--verbose", action="store_true", help="Log page fetching to stderr.")
    args = parser.parse_args(argv)

    ph = PornHub()
    target_url = args.url
    if args.model and args.pornstar:
        parser.error("Choose either --model or --pornstar, not both.")
    if args.model:
        slug = slugify(args.model.strip().replace("_", "-"))
        target_url = f"{BASE_URL}/model/{slug}"
    if args.pornstar:
        slug = slugify(args.pornstar.strip().replace("_", "-"))
        target_url = f"{BASE_URL}/pornstar/{slug}"
    if not target_url:
        parser.error("Provide a performer URL or one of --model/--pornstar.")

    videos, warnings = collect_stream_videos(ph, target_url, max_pages=args.max_pages, verbose=bool(args.verbose))

    payload = {
        "input": target_url,
        "videos": videos,
        **({"warnings": warnings} if warnings else {}),
    }
    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False, default=str)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
