from __future__ import annotations

import argparse
import json
import sys
from urllib.parse import urljoin

from phub import PornHub
from phub.constants import BASE_URL
from phub.parsers import parse_paging
from phub.utils import get_attr, get_soup, text_or_empty


def parse_performers(html: str) -> list[dict]:
    soup = get_soup(html)
    performers = []

    # Pornstar cards
    for li in soup.select("li.pornstarLi.performerCard"):
        name = text_or_empty(li.select_one(".performerCardName"))
        link = li.select_one("a.title")
        href = get_attr(link, "href", "") or ""
        url = urljoin(BASE_URL, href)
        views = text_or_empty(li.select_one(".viewsNumber")).replace("Views", "").strip()
        videos = text_or_empty(li.select_one(".videosNumber")).replace("Videos", "").strip()
        performers.append(
            {
                "type": "pornstar",
                "name": name,
                "url": url,
                "views": views,
                "videos": videos,
            }
        )

    # Model cards
    for li in soup.select("li.modelLi.performerCard"):
        name = text_or_empty(li.select_one(".performerCardName"))
        link = li.select_one("a.title")
        href = get_attr(link, "href", "") or ""
        url = urljoin(BASE_URL, href)
        views = text_or_empty(li.select_one(".viewsNumber")).replace("Views", "").strip()
        videos = text_or_empty(li.select_one(".videosNumber")).replace("Videos", "").strip()
        performers.append(
            {
                "type": "model",
                "name": name,
                "url": url,
                "views": views,
                "videos": videos,
            }
        )

    return performers


def index_performers(ph: PornHub, gender: str | None = None, max_pages: int | None = None) -> list[dict]:
    page = 1
    results: list[dict] = []
    while True:
        params = f"?gender={gender}" if gender else ""
        url = f"{BASE_URL}/pornstars{params}"
        if page > 1:
            url = f"{url}{'&' if params else '?'}page={page}"
        try:
            res = ph.engine.request.get(url)
        except Exception:
            break
        html = res.text
        results.extend(parse_performers(html))
        paging = parse_paging(get_soup(html))
        if max_pages is not None and page >= max_pages:
            break
        if paging.get("isEnd") or (paging.get("maxPage") and page >= paging["maxPage"]):
            break
        page += 1
    return results


def parse_channels(html: str) -> list[dict]:
    soup = get_soup(html)
    channels = []
    for li in soup.select("li.wrap"):
        name = ""
        url = ""

        numbers = li.select_one("div.descriptionContainer ul")
        subs = ""
        videos = ""
        views = ""
        rank = ""
        if numbers:
            alpha_li = numbers.select_one("li.alpha") or numbers.select_one("li")
            link = alpha_li.select_one("a") if alpha_li else None
            if link:
                name = text_or_empty(link)
                href = get_attr(link, "href", "")
                url = urljoin(BASE_URL, href) if href else ""

            items = numbers.select("li")
            for item in items:
                label = text_or_empty(item).lower()
                span_text = text_or_empty(item.select_one("span"))
                if "subscribers" in label:
                    subs = span_text
                elif "videos views" in label:
                    views = span_text
                elif "videos" in label and not videos:
                    videos = span_text
                if "rank" in label:
                    rank = span_text or text_or_empty(item)

        if not name:
            link = li.select_one("a.usernameLink") or li.select_one(".alpha a")
            if link:
                name = text_or_empty(link)
                href = get_attr(link, "href", "")
                url = urljoin(BASE_URL, href) if href else url

        if not rank:
            rank_el = li.select_one(".rank span")
            rank = text_or_empty(rank_el).replace("Rank", "").strip()

        avatar = get_attr(li.select_one(".avatar img"), "src", "")

        channels.append(
            {
                "name": name,
                "url": url,
                "subscribers": subs,
                "videos": videos,
                "views": views,
                "avatar": avatar,
                "rank": rank,
            }
        )
    return channels


def index_channels(ph: PornHub, order: str | None = None, max_pages: int | None = None) -> list[dict]:
    page = 1
    results: list[dict] = []
    while True:
        order_param = f"?o={order}" if order else ""
        url = f"{BASE_URL}/channels{order_param}"
        if page > 1:
            url = f"{url}{'&' if order_param else '?'}page={page}"
        try:
            res = ph.engine.request.get(url)
        except Exception:
            break
        html = res.text
        results.extend(parse_channels(html))
        paging = parse_paging(get_soup(html))
        if max_pages is not None and page >= max_pages:
            break
        if paging.get("isEnd") or (paging.get("maxPage") and page >= paging["maxPage"]):
            break
        page += 1
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Index pornstars/models from the pornstars listing.")
    parser.add_argument("--gender", help="Gender filter for pornstars endpoint (e.g., female, male, m2f, f2m).")
    parser.add_argument("--channel", action="store_true", help="Index channels instead of performers.")
    parser.add_argument("--order", default="rk", help="Channel order param (default rk).")
    parser.add_argument("--max-pages", type=int, default=None, help="Limit pages to fetch.")
    args = parser.parse_args(argv)

    ph = PornHub()
    if args.channel:
        channels = index_channels(ph, order=args.order, max_pages=args.max_pages)
        payload = {"order": args.order, "channels": channels}
    else:
        performers = index_performers(ph, gender=args.gender, max_pages=args.max_pages)
        payload = {"gender": args.gender, "performers": performers}
    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False, default=str)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
    raise SystemExit(main())
