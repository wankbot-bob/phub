from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys

from app.client.rtube.routes import Route
from app.client.rtube.urls import UrlParser


def fetch_with_yt_dlp(url: str) -> dict:
    yt = shutil.which("yt-dlp")
    if not yt:
        return {"error": "yt-dlp not found in PATH"}
    cmd = [yt, "-J", "--no-playlist", url]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=60)
    except Exception as exc:
        return {"error": f"yt-dlp failed to run: {exc}"}
    if result.returncode != 0:
        return {"error": f"yt-dlp exited with {result.returncode}", "stderr": result.stderr.strip()}
    try:
        return {"metadata": json.loads(result.stdout)}
    except Exception as exc:
        return {"error": f"yt-dlp output parse error: {exc}", "raw": result.stdout[:1000]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch Redtube video details by URL or ID.")
    parser.add_argument(
        "url",
        nargs="?",
        help="Video URL or ID (e.g., https://www.redtube.com/123456 or just the numeric id)",
    )
    parser.add_argument("--id", help="Video id shorthand.")
    parser.add_argument("--with-yt-dlp", action="store_true", help="Also run yt-dlp -J on the URL and include the metadata.")
    args = parser.parse_args(argv)

    target = args.url or args.id
    if not target:
        parser.error("Provide a video URL/ID or --id.")

    video_url = Route.resolve_video(target)
    yt_dlp = fetch_with_yt_dlp(video_url) if args.with_yt_dlp else None

    payload = {
        "input": target,
        "video_url": video_url,
        **({"video_data": yt_dlp} if yt_dlp is not None else {}),
    }
    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False, default=str)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
