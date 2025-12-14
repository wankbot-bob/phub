from __future__ import annotations

import argparse
import json
import sys
import shutil
import subprocess

from phub import PornHub
from phub.errors import HttpStatusError


def fetch_with_yt_dlp(url: str) -> dict:
    """
    Try to fetch rich metadata using yt-dlp -J.
    """
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
    parser = argparse.ArgumentParser(description="Fetch video details from Pornhub by URL or viewkey.")
    parser.add_argument("url", help="Video URL or viewkey (e.g., https://www.pornhub.com/view_video.php?viewkey=XXXX)")
    parser.add_argument("--with-yt-dlp", action="store_true", help="Also run yt-dlp -J on the URL and include the metadata.")
    args = parser.parse_args(argv)

    ph = PornHub()
    video = None
    video_error = None
    try:
        video = ph.video(args.url)
    except HttpStatusError as exc:
        video_error = f"{exc}"
    except Exception as exc:
        video_error = f"{type(exc).__name__}: {exc}"

    yt_dlp = fetch_with_yt_dlp(args.url) if args.with_yt_dlp else None

    payload = {
        "input": args.url,
        **({"video": video} if video is not None else {}),
        **({"video_error": video_error} if video_error else {}),
        **({"video_data": yt_dlp} if yt_dlp is not None else {}),
    }
    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False, default=str)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
