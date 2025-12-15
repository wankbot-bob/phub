from __future__ import annotations

import argparse
import json
import sys
import shutil
import subprocess
import tempfile
import os
from http.cookiejar import MozillaCookieJar
from urllib.parse import urlparse

from requests.cookies import create_cookie

from app.client.phub import PornHub
from app.client.phub.errors import HttpStatusError
from app.client.phub.constants import BASE_URL
from app.client.phub.urls import UrlParser


def _write_cookies_file(url: str, cookies: dict[str, str]) -> str | None:
    """
    Persist cookies to a temporary Netscape cookie jar so yt-dlp can reuse the session.
    """
    if not cookies:
        return None
    host = urlparse(url).hostname or "www.pornhub.com"
    jar = MozillaCookieJar()
    for name, value in cookies.items():
        jar.set_cookie(create_cookie(name=name, value=value, domain=host, path="/"))
    tmp = tempfile.NamedTemporaryFile(prefix="yt-dlp-cookies-", suffix=".txt", delete=False)
    jar.save(tmp.name, ignore_discard=True, ignore_expires=True)
    tmp.close()
    return tmp.name


def fetch_with_yt_dlp(url: str, cookies: dict[str, str] | None = None) -> dict:
    """
    Try to fetch rich metadata using yt-dlp -J.
    """
    yt = shutil.which("yt-dlp")
    if not yt:
        return {"error": "yt-dlp not found in PATH"}

    cookie_file = None
    cmd = [yt, "-J", "--no-playlist"]
    try:
        if cookies:
            cookie_file = _write_cookies_file(url, cookies)
            if cookie_file:
                cmd += ["--cookies", cookie_file]
    except Exception as exc:
        # Continue without cookies but surface the failure
        return {"error": f"failed to prepare cookies for yt-dlp: {exc}"}

    cmd.append(url)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=60)
    except Exception as exc:
        return {"error": f"yt-dlp failed to run: {exc}"}
    finally:
        if cookie_file:
            try:
                os.remove(cookie_file)
            except Exception:
                pass

    if result.returncode != 0:
        return {"error": f"yt-dlp exited with {result.returncode}", "stderr": result.stderr.strip()}

    try:
        return {"metadata": json.loads(result.stdout)}
    except Exception as exc:
        return {"error": f"yt-dlp output parse error: {exc}", "raw": result.stdout[:1000]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch video details from Pornhub by URL or viewkey.")
    parser.add_argument(
        "url",
        nargs="?",
        help="Video URL or viewkey (e.g., https://www.pornhub.com/view_video.php?viewkey=XXXX or just the key)",
    )
    parser.add_argument("--viewkey", help="Viewkey shorthand (alternative to positional URL).")
    parser.add_argument("--with-yt-dlp", action="store_true", help="Also run yt-dlp -J on the URL and include the metadata.")
    args = parser.parse_args(argv)

    target = args.url or args.viewkey
    if not target:
        parser.error("Provide a video URL or --viewkey.")

    viewkey = UrlParser.get_video_id(target)
    target_url = target if target.startswith("http") else f"{BASE_URL}/view_video.php?viewkey={viewkey}"

    ph = PornHub()
    video = None
    video_error = None
    try:
        video = ph.video(viewkey)
    except HttpStatusError as exc:
        video_error = f"{exc}"
    except Exception as exc:
        video_error = f"{type(exc).__name__}: {exc}"

    cookies = ph.engine.request.get_cookies()
    yt_dlp = fetch_with_yt_dlp(target_url, cookies) if args.with_yt_dlp else None

    payload = {
        "input": target,
        "viewkey": viewkey,
        "url": target_url,
        **({"video": video} if video is not None else {}),
        **({"video_error": video_error} if video_error else {}),
        **({"video_data": yt_dlp} if yt_dlp is not None else {}),
        **({"warnings": [yt_dlp["error"]]} if yt_dlp and yt_dlp.get("error") else {}),
    }
    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False, default=str)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
