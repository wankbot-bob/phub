from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from app.client.rtube.parsers import parse_video_list
from app.client.rtube.routes import Route
from app.client.rtube.urls import UrlParser
from app.core.utils import get_soup
from app.client.phub.http import Request


def collect_channel(url: str, max_pages: int | None = None, *, verbose: bool = False) -> dict:
    slug = UrlParser.get_channel_slug(url)
    request = Request()
    videos: list[dict[str, Any]] = []
    page = 1
    while True:
        page_url = Route.channel_page(slug, page)
        if verbose:
            print(f"[rtube channel] fetch {page_url}", file=sys.stderr)
        res = request.get(page_url)
        page_items = parse_video_list(res.text)
        if not page_items:
            break
        videos.extend(page_items)
        if max_pages is not None and page >= max_pages:
            break
        page += 1
    return {"input": url, "slug": slug, "videos": videos, "paging": {"current": page, "isEnd": True}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch Redtube channel videos.")
    parser.add_argument("url", nargs="?", help="Channel URL or slug")
    parser.add_argument("--channel", help="Channel slug (shortcut for https://www.redtube.com/channels/{slug})")
    parser.add_argument("--max-pages", type=int, default=None, help="Limit how many pages to fetch.")
    parser.add_argument("--verbose", action="store_true", help="Log page fetching to stderr.")
    args = parser.parse_args(argv)

    target = args.url
    if args.channel:
        target = f"https://www.redtube.com/channels/{args.channel.strip()}"
    if not target:
        parser.error("Provide a channel URL/slug or --channel.")

    result = collect_channel(target, max_pages=args.max_pages, verbose=bool(args.verbose))
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False, default=str)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
