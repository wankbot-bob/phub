from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import sys
from typing import Any
from urllib.parse import urljoin, urlparse

from app.client.phub import PornHub
from app.client.phub.constants import BASE_URL
from app.client.phub.errors import HttpStatusError
from app.client.phub.parsers import parse_counting, parse_paging, parse_video_result
from app.client.phub.urls import UrlParser
from app.core.logging import verbose_print
from app.core.trailers import build_trailer_map
from app.core.utils import get_attr, get_data, get_soup, remove_protection_bracket, text_or_empty, slugify


def _get_soup_cached(ph: PornHub, url: str, cache: dict[str, Any] | None = None):
    """
    Fetch and cache soup for a URL to avoid duplicate requests on the same page.
    """
    cache = cache if cache is not None else {}
    if url in cache:
        return cache[url]
    res = ph.engine.request.get(url)
    soup = get_soup(res.text)
    cache[url] = soup
    return soup


def detect_kind(url: str) -> str:
    path = urlparse(url).path.lower()
    if "/model/" in path:
        return "model"
    if "/pornstar/" in path:
        return "pornstar"
    raise ValueError("URL must contain /model/ or /pornstar/")


def _fallback_profile(ph: PornHub, url: str, *, soup_cache: dict[str, Any] | None = None) -> dict:
    try:
        soup = _get_soup_cached(ph, url, soup_cache)
        name = text_or_empty(soup.select_one(".nameSubscribe .name")) or text_or_empty(
            soup.select_one("head > title")
        ).replace("- Pornhub.com", "").strip()
        avatar = get_attr(soup.select_one("img#getAvatar"), "src", "")
        cover = get_attr(soup.select_one("img#coverPictureDefault"), "src", "")
        return {"name": name, "avatar": avatar, "cover": cover}
    except Exception:
        # fallback to slug as name
        slug = urlparse(url).path.rstrip("/").split("/")[-1]
        return {"name": slug, "avatar": "", "cover": ""}


def _fallback_videos(ph: PornHub, url: str, *, soup_cache: dict[str, Any] | None = None) -> tuple[list[dict], dict | None, dict | None]:
    try:
        soup = _get_soup_cached(ph, url, soup_cache)
        items = []
        items.extend(parse_video_result(soup, ".videoUList"))
        items.extend(parse_video_result(soup, ".pornstarUploadedVideos"))
        items.extend(parse_video_result(soup, ".mostRecentPornstarVideos"))

        trailer_map = build_trailer_map(soup)

        enriched_items = []
        for item in items:
            vkey = UrlParser.get_video_id(item.get("url") or item.get("id") or "")
            trailer = trailer_map.get(vkey)
            if trailer:
                item = {**item, "trailer": trailer}
            enriched_items.append(item)

        paging = parse_paging(soup)
        counting = {"from": 0, "to": 0, "total": len(enriched_items)}
        return enriched_items, paging, counting
    except Exception:
        return [], None, None


def _enrich_with_trailers(ph: PornHub, url: str, videos: list[dict], *, soup_cache: dict[str, Any] | None = None) -> list[dict]:
    """
    Attach mediabook/trailer URLs to videos when available on the performer page.
    """
    if not videos:
        return videos
    try:
        soup = _get_soup_cached(ph, url, soup_cache)
    except Exception:
        return videos
    trailer_map = build_trailer_map(soup)

    enriched = []
    for video in videos:
        vkey = UrlParser.get_video_id(video.get("url") or video.get("id") or "")
        trailer = trailer_map.get(vkey)
        if trailer:
            video = {**video, "trailer": trailer}
        enriched.append(video)

    return enriched


def _enrich_video_details(
    ph: PornHub, videos: list[dict], *, max_workers: int = 5, timeout: float = 10.0, total_timeout: float | None = None
) -> list[dict]:
    """
    Optionally fetch each video page (in parallel) to fill preview/views/duration/title.
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

    if not videos:
        return videos

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


def fetch_gifs(ph: PornHub, gifs_url: str) -> tuple[list[dict], list[str]]:
    """
    Fetch all GIFs by paging through the /gifs/video listing.
    """
    page = 1
    gifs: list[dict] = []
    warnings: list[str] = []
    soup_cache: dict[str, Any] = {}
    while True:
        try:
            url = gifs_url.rstrip("/") + "/video"
            if page > 1:
                url = f"{url}?page={page}"
            soup = _get_soup_cached(ph, url, soup_cache)
        except HttpStatusError as exc:
            warnings.append(f"gifs: {exc}")
            break
        except Exception:
            warnings.append("gifs: fetch failed")
            break

        page_items = []
        for item in soup.select("ul.gifLink li.gifVideoBlock"):
            video = item.find("video")
            poster = (
                get_attr(video, "poster", "")
                or get_attr(video, "data-poster", "")
                or get_attr(video, "data-image", "")
                or ""
            )
            path = get_attr(item.find("a"), "href", "") or ""
            page_items.append(
                {
                    "title": text_or_empty(item.select_one(".title")),
                    "url": urljoin(BASE_URL, path),
                    "mp4": get_data(video, "mp4", "") if video else "",
                    "webm": get_data(video, "webm", "") if video else "",
                    "preview": remove_protection_bracket(poster),
                }
            )

        if not page_items:
            break

        gifs.extend(page_items)

        paging = parse_paging(soup)
        max_page = paging.get("maxPage")
        if paging.get("isEnd") or (isinstance(max_page, int) and page >= max_page):
            break
        page += 1

    return gifs, warnings


def fetch_albums(ph: PornHub, albums_url: str) -> tuple[list[dict], list[str]]:
    """
    Fetch albums with pagination support and fallback selectors.
    """
    soup_cache: dict[str, Any] = {}
    warnings: list[str] = []
    def parse_page(soup) -> tuple[list[dict], dict]:
        blocks = soup.select("ul#photosAlbumsSection li.photoAlbumListContainer div.photoAlbumListBlock")
        if not blocks:
            blocks = soup.select("div.photoAlbumListBlock")
        found = []
        for item in blocks:
            title = get_attr(item, "title", "") or ""
            path = get_attr(item.find("a"), "href", "") or ""
            rating = text_or_empty(item.select_one(".album-photo-percentage"))
            preview = get_data(item, "bkg", "") or ""
            if not preview:
                style = get_attr(item, "style", "")
                if style:
                    import re as _re

                    m = _re.search(r'url\("(.+)"\)', style)
                    if m:
                        preview = m.group(1)
            found.append(
                {
                    "title": title,
                    "url": urljoin(BASE_URL, path) if path else "",
                    "rating": rating,
                    "preview": preview,
                }
            )
        return found, parse_paging(soup)

    albums: list[dict] = []
    seen_urls = set()
    base_urls = [albums_url.rstrip("/"), albums_url.rstrip("/").replace("/albums", "/images")]

    for base in base_urls:
        page = 1
        while True:
            try:
                url = base
                if page > 1:
                    url = f"{base}?page={page}"
                soup = _get_soup_cached(ph, url, soup_cache)
            except HttpStatusError as exc:
                warnings.append(f"albums: {exc}")
                break
            except Exception:
                warnings.append("albums: fetch failed")
                break

            page_albums, paging = parse_page(soup)
            page_albums = [a for a in page_albums if not a["url"] or a["url"] not in seen_urls]
            for a in page_albums:
                if a["url"]:
                    seen_urls.add(a["url"])
            albums.extend(page_albums)

            if not page_albums:
                break
            # Continue until no results; rely on empty page exit
            page += 1

    # Final fallback: try main performer page for inline album blocks
    if not albums:
        try:
            base_url = albums_url.rsplit("/albums", 1)[0]
            base_soup = _get_soup_cached(ph, base_url, soup_cache)
            base_albums, _ = parse_page(base_soup)
            albums.extend(base_albums)
        except HttpStatusError:
            warnings.append("albums: fallback 404/403")
        except Exception:
            warnings.append("albums: fallback failed")

    return albums, warnings


def collect_model(
    ph: PornHub,
    url: str,
    *,
    enrich_details: bool = False,
    max_workers: int = 5,
    detail_timeout: float = 10.0,
    detail_total_timeout: float | None = None,
    verbose: bool = False,
) -> dict:
    soup_cache: dict[str, Any] = {}
    profile = ph.model(url)
    if not profile.get("name"):
        profile.update(_fallback_profile(ph, url, soup_cache=soup_cache))

    # paginate uploaded videos by scraping pages to capture trailers
    videos = []
    page = 1
    paging = None
    counting = None
    slug = UrlParser.get_model_name(url)
    while True:
        try:
            page_url = f"{BASE_URL}/model/{slug}/videos"
            if page > 1:
                page_url = f"{page_url}?page={page}"
            res = ph.engine.request.get(page_url)
            soup = get_soup(res.text)
        except Exception:
            break

        verbose_print(verbose, f"[performer] fetch page {page_url}")
        page_items = parse_video_result(soup, ".videoUList") or parse_video_result(soup, "li.videoblock")

        # attach trailers from data-mediabook
        trailer_map = build_trailer_map(soup)
        enriched_page = []
        for item in page_items:
            vkey = UrlParser.get_video_id(item.get("url") or item.get("id") or "")
            trailer = trailer_map.get(vkey)
            if trailer:
                item = {**item, "trailer": trailer}
            enriched_page.append(item)

        videos.extend(enriched_page)

        paging = parse_paging(soup)
        counting_info = parse_counting(soup)
        if counting_info["total"] and counting_info["to"] >= counting_info["from"]:
            counting = counting_info
        else:
            counting = {"from": 0, "to": len(videos), "total": len(videos)}

        max_page = paging.get("maxPage")
        if not page_items:
            verbose_print(verbose, "[performer] stopping: empty page")
            break
        if paging.get("isEnd") or (isinstance(max_page, int) and page >= max_page):
            reason = "isEnd" if paging.get("isEnd") else "maxPage reached"
            verbose_print(verbose, f"[performer] stopping: {reason}")
            break
        if counting_info["total"] and counting_info["to"] >= counting_info["from"]:
            per_page = counting_info["to"] - counting_info["from"] + 1
            if per_page > 0:
                pages_total = math.ceil(counting_info["total"] / per_page)
                if page >= pages_total:
                    verbose_print(verbose, "[performer] stopping: counted total reached")
                    break
        page += 1

    if not videos:
        videos, paging, counting = _fallback_videos(ph, url, soup_cache=soup_cache)
    videos = _enrich_with_trailers(ph, url, videos, soup_cache=soup_cache)
    if enrich_details:
        videos = _enrich_video_details(
            ph, videos, max_workers=max_workers, timeout=detail_timeout, total_timeout=detail_total_timeout
        )
    gifs, gif_warnings = fetch_gifs(ph, url.rstrip("/") + "/gifs")
    albums, album_warnings = fetch_albums(ph, url.rstrip("/") + "/albums")
    warnings = [*gif_warnings, *album_warnings]

    return {
        "profile": profile,
        "uploadedVideos": videos,
        "videos": {
            "source": "model_videos",
            "items": videos,
            "paging": paging,
            "counting": counting,
        },
        "gifs": gifs,
        "albums": albums,
        **({"warnings": warnings} if warnings else {}),
    }


def collect_pornstar(
    ph: PornHub,
    url: str,
    *,
    enrich_details: bool = False,
    max_workers: int = 5,
    detail_timeout: float = 10.0,
    detail_total_timeout: float | None = None,
    verbose: bool = False,
) -> dict:
    soup_cache: dict[str, Any] = {}
    profile = ph.pornstar(url)
    if not profile.get("name"):
        profile.update(_fallback_profile(ph, url, soup_cache=soup_cache))
    uploaded = profile.get("uploadedVideos") or []
    tagged = profile.get("mostRecentVideos") or []

    # Paginate uploaded videos explicitly to gather multiple pages (try uploaded then general videos)
    slug = UrlParser.get_pornstar_name(url)
    for base_path in [
        f"{BASE_URL}/pornstar/{slug}/videos/uploaded",
        f"{BASE_URL}/pornstar/{slug}/videos",
    ]:
        page = 1
        while True:
            try:
                page_url = base_path if page == 1 else f"{base_path}?page={page}"
                verbose_print(verbose, f"[performer] fetch page {page_url}")
                res = ph.engine.request.get(page_url)
                soup = get_soup(res.text)
            except Exception:
                break

            page_items = parse_video_result(soup, ".videoUList") or parse_video_result(soup, "li.videoblock")
            trailer_map = build_trailer_map(soup)
            enriched_page = []
            for item in page_items:
                vkey = UrlParser.get_video_id(item.get("url") or item.get("id") or "")
                trailer = trailer_map.get(vkey)
                if trailer:
                    item = {**item, "trailer": trailer}
                enriched_page.append(item)
            uploaded.extend(enriched_page)

            paging = parse_paging(soup)
            counting_info = parse_counting(soup)
            max_page = paging.get("maxPage")
            if not page_items:
                verbose_print(verbose, f"[performer] stopping pornstar uploads at {page_url}: empty page")
                break
            if paging.get("isEnd") or (isinstance(max_page, int) and page >= max_page):
                break
            if counting_info["total"] and counting_info["to"] >= counting_info["from"]:
                per_page = counting_info["to"] - counting_info["from"] + 1
                if per_page > 0:
                    pages_total = math.ceil(counting_info["total"] / per_page)
                    if page >= pages_total:
                        break
            page += 1

    # If still empty, try fallback scraping once
    if not uploaded and not tagged:
        uploaded, _, _ = _fallback_videos(ph, url, soup_cache=soup_cache)

    uploaded = _enrich_with_trailers(ph, url, uploaded, soup_cache=soup_cache)
    tagged = _enrich_with_trailers(ph, url, tagged, soup_cache=soup_cache)
    if enrich_details:
        uploaded = _enrich_video_details(
            ph, uploaded, max_workers=max_workers, timeout=detail_timeout, total_timeout=detail_total_timeout
        )
        tagged = _enrich_video_details(
            ph, tagged, max_workers=max_workers, timeout=detail_timeout, total_timeout=detail_total_timeout
        )
    gifs, gif_warnings = fetch_gifs(ph, url.rstrip("/") + "/gifs")
    albums, album_warnings = fetch_albums(ph, url.rstrip("/") + "/albums")
    warnings = [*gif_warnings, *album_warnings]
    return {
        "profile": profile,
        "videos": {
            "source": "uploaded/mostRecent",
            "items": uploaded or tagged,
            "uploadedVideos": uploaded,
            "mostRecentVideos": tagged,
        },
        "gifs": gifs,
        "albums": albums,
        **({"warnings": warnings} if warnings else {}),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch performer profile and media from Pornhub.")
    parser.add_argument(
        "url",
        nargs="?",
        help="Performer URL (https://www.pornhub.com/model/{name} or /pornstar/{name})",
    )
    parser.add_argument("--model", help="Model slug (shortcut for https://www.pornhub.com/model/{name})")
    parser.add_argument("--pornstar", help="Pornstar slug (shortcut for https://www.pornhub.com/pornstar/{name})")
    parser.add_argument(
        "--enrich-details",
        action="store_true",
        help="Fetch each video page to fill preview/views/duration/title (thread pool, slower).",
    )
    parser.add_argument("--workers", type=int, default=5, help="Worker threads for detail enrichment.")
    parser.add_argument("--detail-timeout", type=float, default=10.0, help="Per-video detail fetch timeout in seconds.")
    parser.add_argument(
        "--detail-total-timeout",
        type=float,
        default=None,
        help="Overall timeout for detail enrichment (defaults to timeout * videos).",
    )
    parser.add_argument("--verbose", action="store_true", help="Log page fetching and loop stop reasons to stderr.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    ph = PornHub()
    # Determine target URL/kind from flags or positional
    target_url = args.url
    kind = None
    if args.model and args.pornstar:
        parser.error("Choose either --model or --pornstar, not both.")
    if args.model:
        slug = slugify(args.model.strip().replace("_", "-"))
        target_url = f"{BASE_URL}/model/{slug}"
        kind = "model"
    elif args.pornstar:
        slug = slugify(args.pornstar.strip().replace("_", "-"))
        target_url = f"{BASE_URL}/pornstar/{slug}"
        kind = "pornstar"
    elif target_url:
        kind = detect_kind(target_url)
    else:
        parser.error("Provide a performer URL or one of --model/--pornstar.")

    if kind == "model":
        result = collect_model(
            ph,
            target_url,
            enrich_details=bool(args.enrich_details),
            max_workers=args.workers,
            detail_timeout=args.detail_timeout,
            detail_total_timeout=args.detail_total_timeout,
            verbose=bool(args.verbose),
        )
    else:
        result = collect_pornstar(
            ph,
            target_url,
            enrich_details=bool(args.enrich_details),
            max_workers=args.workers,
            detail_timeout=args.detail_timeout,
            detail_total_timeout=args.detail_total_timeout,
            verbose=bool(args.verbose),
        )

    payload = {
        "input": target_url,
        "kind": kind,
        **result,
    }
    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False, default=str)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
