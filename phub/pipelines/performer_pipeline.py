from __future__ import annotations

import argparse
import json
import sys
from urllib.parse import urljoin, urlparse

from phub import PornHub
from phub.constants import BASE_URL
from phub.parsers import parse_paging, parse_video_result
from phub.urls import UrlParser
from phub.utils import get_attr, get_data, get_soup, remove_protection_bracket, text_or_empty


def detect_kind(url: str) -> str:
    path = urlparse(url).path.lower()
    if "/model/" in path:
        return "model"
    if "/pornstar/" in path:
        return "pornstar"
    raise ValueError("URL must contain /model/ or /pornstar/")


def _warmup(ph: PornHub):
    try:
        ph.engine.request.get(BASE_URL + "/")
    except Exception:
        pass


def _fallback_profile(ph: PornHub, url: str) -> dict:
    try:
        res = ph.engine.request.get(url)
        soup = get_soup(res.text)
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


def _fallback_videos(ph: PornHub, url: str) -> tuple[list[dict], dict | None, dict | None]:
    try:
        res = ph.engine.request.get(url)
        soup = get_soup(res.text)
        items = []
        items.extend(parse_video_result(soup, ".videoUList"))
        items.extend(parse_video_result(soup, ".pornstarUploadedVideos"))
        items.extend(parse_video_result(soup, ".mostRecentPornstarVideos"))

        trailer_map: dict[str, str] = {}
        for li in soup.select("li[data-video-vkey] [data-mediabook]"):
            parent_li = li.find_parent("li", attrs={"data-video-vkey": True})
            vkey = parent_li.get("data-video-vkey") if parent_li else None
            trailer = get_attr(li, "data-mediabook", "") or get_data(li, "mediabook", "")
            if vkey and trailer:
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


def _enrich_with_trailers(ph: PornHub, url: str, videos: list[dict]) -> list[dict]:
    """
    Attach mediabook/trailer URLs to videos when available on the performer page.
    """
    if not videos:
        return videos
    try:
        res = ph.engine.request.get(url)
    except Exception:
        return videos

    soup = get_soup(res.text)
    trailer_map: dict[str, str] = {}

    # Prefer li items that carry the video vkey
    for li in soup.select("li[data-video-vkey]"):
        vkey = li.get("data-video-vkey")
        if not vkey:
            continue
        node = li.select_one("[data-mediabook]")
        if node:
            trailer = get_attr(node, "data-mediabook", "") or get_data(node, "mediabook", "")
            if trailer:
                trailer_map[vkey] = trailer

    # Fallback: any mediabook element with a link containing a viewkey
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


def fetch_gifs(ph: PornHub, gifs_url: str) -> list[dict]:
    """
    Fetch all GIFs by paging through the /gifs/video listing.
    """
    page = 1
    gifs: list[dict] = []
    while True:
        try:
            url = gifs_url.rstrip("/") + "/video"
            if page > 1:
                url = f"{url}?page={page}"
            res = ph.engine.request.get(url)
        except Exception:
            break

        soup = get_soup(res.text)
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
        if paging.get("isEnd") or (paging.get("maxPage") and page >= paging["maxPage"]):
            break
        page += 1

    return gifs


def fetch_albums(ph: PornHub, albums_url: str) -> list[dict]:
    """
    Fetch albums with pagination support and fallback selectors.
    """
    _warmup(ph)
    def parse_page(res_html: str) -> list[dict]:
        soup = get_soup(res_html)
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
                res = ph.engine.request.get(url)
            except Exception:
                break

            page_albums, paging = parse_page(res.text)
            page_albums = [a for a in page_albums if not a["url"] or a["url"] not in seen_urls]
            for a in page_albums:
                if a["url"]:
                    seen_urls.add(a["url"])
            albums.extend(page_albums)

            if not page_albums:
                break
            # Continue until no results; don't trust paging when missing
            if page >= 50:  # safety cap
                break
            page += 1

    # Final fallback: try main performer page for inline album blocks
    if not albums:
        try:
            base_res = ph.engine.request.get(albums_url.rsplit("/albums", 1)[0])
            base_albums, _ = parse_page(base_res.text)
            albums.extend(base_albums)
        except Exception:
            pass

    return albums


def collect_model(ph: PornHub, url: str) -> dict:
    _warmup(ph)
    profile = ph.model(url)
    if not profile.get("name"):
        profile.update(_fallback_profile(ph, url))

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

        page_items = parse_video_result(soup, ".videoUList") or parse_video_result(soup, "li.videoblock")

        # attach trailers from data-mediabook
        trailer_map: dict[str, str] = {}
        for node in soup.select("li[data-video-vkey] [data-mediabook]"):
            vkey = node.find_parent("li").get("data-video-vkey") if node.find_parent("li") else None
            trailer = get_attr(node, "data-mediabook", "") or get_data(node, "mediabook", "")
            if vkey and trailer:
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
        enriched_page = []
        for item in page_items:
            vkey = UrlParser.get_video_id(item.get("url") or item.get("id") or "")
            trailer = trailer_map.get(vkey)
            if trailer:
                item = {**item, "trailer": trailer}
            enriched_page.append(item)

        videos.extend(enriched_page)

        paging = parse_paging(soup)
        counting = {"from": 0, "to": 0, "total": len(videos)}

        if paging.get("isEnd") or (paging.get("maxPage") and page >= paging["maxPage"]):
            break
        page += 1

    if not videos:
        videos, paging, counting = _fallback_videos(ph, url)
    videos = _enrich_with_trailers(ph, url, videos)
    gifs = fetch_gifs(ph, url.rstrip("/") + "/gifs")
    albums = fetch_albums(ph, url.rstrip("/") + "/albums")

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
    }


def collect_pornstar(ph: PornHub, url: str) -> dict:
    _warmup(ph)
    profile = ph.pornstar(url)
    if not profile.get("name"):
        profile.update(_fallback_profile(ph, url))
    uploaded = profile.get("uploadedVideos") or []
    tagged = profile.get("mostRecentVideos") or []
    # If no videos, try fallback scraping once
    if not uploaded and not tagged:
        uploaded, _, _ = _fallback_videos(ph, url)
    uploaded = _enrich_with_trailers(ph, url, uploaded)
    tagged = _enrich_with_trailers(ph, url, tagged)
    gifs = fetch_gifs(ph, url.rstrip("/") + "/gifs")
    albums = fetch_albums(ph, url.rstrip("/") + "/albums")
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
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch performer profile and media from Pornhub.")
    parser.add_argument("url", help="Performer URL (https://www.pornhub.com/model/{name} or /pornstar/{name})")
    args = parser.parse_args(argv)

    ph = PornHub()
    kind = detect_kind(args.url)

    if kind == "model":
        result = collect_model(ph, args.url)
    else:
        result = collect_pornstar(ph, args.url)

    payload = {
        "input": args.url,
        "kind": kind,
        **result,
    }
    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False, default=str)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
