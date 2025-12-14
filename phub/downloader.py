from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any, Iterable, List, Tuple


def _iter_entries(media_definitions: Iterable[dict[str, Any]]):
    for item in media_definitions:
        url = item.get("videoUrl")
        q_field = item.get("quality", [])
        qualities = q_field if isinstance(q_field, list) else [q_field]
        default_raw = item.get("defaultQuality")
        for q in qualities:
            try:
                q_int = int(q)
            except Exception:
                continue
            default_flag = bool(default_raw) or (isinstance(default_raw, (int, float)) and int(default_raw) == q_int)
            yield {"url": url, "quality": q_int, "default": default_flag}


def choose_media_url(media_definitions: Iterable[dict[str, Any]], quality: int | None = None) -> Tuple[str, int]:
    """
    Select a media URL from mediaDefinitions, preferring the requested quality,
    else the default flagged entry, else the highest available quality.
    """
    entries = list(_iter_entries(media_definitions))
    if not entries:
        raise ValueError("No media definitions available to choose from")

    if quality is not None:
        matched = [e for e in entries if e["quality"] == quality]
        if matched:
            picked = matched[0]
            return picked["url"], picked["quality"]

    default_entries = [e for e in entries if e["default"]]
    if default_entries:
        picked = max(default_entries, key=lambda e: e["quality"])
    else:
        picked = max(entries, key=lambda e: e["quality"])

    return picked["url"], picked["quality"]


def download_with_ytdlp(
    media_definitions: Iterable[dict[str, Any]],
    *,
    output: str | Path | None = None,
    quality: int | None = None,
    extra_args: List[str] | None = None,
) -> dict[str, Any]:
    """
    Download a video using yt-dlp from the provided mediaDefinitions list.

    Args:
        media_definitions: List of media definition dictionaries (from videoPage).
        output: Optional output template/path for yt-dlp (-o).
        quality: Desired numeric quality (e.g., 720). Defaults to highest/default.
        extra_args: Additional arguments to forward to yt-dlp.
    """
    yt_dlp_path = shutil.which("yt-dlp")
    if not yt_dlp_path:
        raise FileNotFoundError("yt-dlp not found in PATH. Install it first.")

    url, selected_quality = choose_media_url(media_definitions, quality)
    cmd = [yt_dlp_path, url]
    if output:
        cmd += ["-o", str(output)]
    if extra_args:
        cmd.extend(extra_args)

    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed with exit code {result.returncode}")

    return {"url": url, "quality": selected_quality, "returncode": result.returncode}
