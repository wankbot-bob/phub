# PHUB (Python)

Python port of the `pornhub.js` library. It scrapes Pornhub pages (videos, channels, models, pornstars, albums, photos), performs searches, and exposes the official WebMaster API.

## Installation

```bash
make install   # creates .venv, installs Poetry + deps
```

## Quickstart

```python
from phub import PornHub

ph = PornHub()

# Video details
video = ph.video("https://www.pornhub.com/view_video.php?viewkey=ph5ac81eabe203d")
print(video["title"], video["durationFormatted"])

# Search videos
results = ph.search_video("tokyo hot")
print(results["data"][0])

# WebMaster API
active = ph.webMaster.is_video_active("ph5ac81eabe203d")
print("Is active:", active)
```

Set `dump_page=True` (or a folder path) when creating `PornHub()` to archive raw HTML/JSON responses for debugging.

## Features
- Page scrapers: video, album, photo, pornstar, model, channel, random, recommended
- Search: videos, albums, gifs, channels, pornstars, models (autocomplete)
- Lists: videos, pornstars
- Account: login/logout helpers
- WebMaster API: search, metadata, embed codes, tags, categories, stars, deleted videos

## Downloading with yt-dlp
We still don't ship a downloader, but you can pass `mediaDefinitions` to `yt-dlp`.

```bash
python -m pip install yt-dlp  # optional, outside of Poetry if you prefer
```

```python
from phub import PornHub, download_with_ytdlp

ph = PornHub()
video = ph.video("https://www.pornhub.com/view_video.php?viewkey=ph5ac81eabe203d")

# pick default/highest stream and download via yt-dlp
download_with_ytdlp(video["mediaDefinitions"], output="%(title)s.%(ext)s")

# or request a specific quality (e.g., 720p)
download_with_ytdlp(video["mediaDefinitions"], quality=720)
```

`download_with_ytdlp` chooses the requested quality if available, otherwise the default flag, otherwise the highest quality stream.

## Notes
- The client sets cookies/headers to bypass age prompts; use responsibly and respect Pornhub's terms.
