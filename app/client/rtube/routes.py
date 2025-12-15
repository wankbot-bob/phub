from __future__ import annotations

from app.client.rtube.constants import BASE_URL
from app.client.rtube.urls import UrlParser


class Route:
    @staticmethod
    def video_page(video_id: str) -> str:
        return f"{BASE_URL}/{video_id}"

    @staticmethod
    def performer_page(slug: str, page: int | None = None) -> str:
        suffix = f"?page={page}" if page and page > 1 else ""
        return f"{BASE_URL}/pornstar/{slug}{suffix}"

    @staticmethod
    def channel_page(slug: str, page: int | None = None) -> str:
        suffix = f"?page={page}" if page and page > 1 else ""
        return f"{BASE_URL}/channels/{slug}{suffix}"

    @staticmethod
    def resolve_video(url_or_id: str) -> str:
        vid = UrlParser.get_video_id(url_or_id)
        return Route.video_page(vid)
