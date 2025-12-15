from __future__ import annotations

from typing import Any, Dict, List

from .engine import Engine
from .routes import WebmasterRoute
from .urls import UrlParser


def _video_transform(response: Dict[str, Any]) -> Dict[str, Any]:
    duration = response.get("duration")
    views = response.get("views")
    video_id = response.get("video_id")
    rating = response.get("rating", 0)
    ratings = response.get("ratings", 0)
    title = response.get("title")
    url = response.get("url")
    default_thumb = response.get("default_thumb")
    thumb = response.get("thumb")
    publish_date = response.get("publish_date")
    thumbs = [{"width": t.get("width"), "height": t.get("height"), "src": t.get("src")} for t in response.get("thumbs", [])]
    tags = [tag.get("tag_name") for tag in response.get("tags", [])]
    pornstars = [ps.get("pornstar_name") for ps in response.get("pornstars", [])]
    categories = [c.get("category") for c in response.get("categories", [])]
    segment = response.get("segment")

    total = ratings
    up = round(total * rating / 100) if total else 0
    down = total - up
    vote = {"up": up, "down": down, "total": total, "rating": round(rating, 2)}

    return {
        "duration": duration,
        "views": views,
        "video_id": video_id,
        "vote": vote,
        "title": title,
        "url": url,
        "default_thumb": default_thumb,
        "thumb": thumb,
        "publish_date": publish_date,
        "thumbs": thumbs,
        "tags": tags,
        "pornstars": pornstars,
        "categories": categories,
        "segment": segment,
    }


def search(engine: Engine, keyword: str, **options: Any) -> List[Dict[str, Any]]:
    try:
        res = engine.request.get(WebmasterRoute.search(keyword, **options))
        data = res.json()
        return [_video_transform(item) for item in data.get("videos", [])]
    except Exception:
        return []


def get_video(engine: Engine, url_or_id: str, thumbsize: str = "large") -> Dict[str, Any]:
    video_id = UrlParser.get_video_id(url_or_id)
    res = engine.request.get(WebmasterRoute.video_by_id(video_id, thumbsize))
    data = res.json()
    return _video_transform(data.get("video", {}))


def is_video_active(engine: Engine, url_or_id: str) -> bool:
    video_id = UrlParser.get_video_id(url_or_id)
    res = engine.request.get(WebmasterRoute.is_video_active(video_id))
    payload = res.json()
    return bool(payload.get("active", False))


def get_video_embed_code(engine: Engine, url_or_id: str) -> str:
    video_id = UrlParser.get_video_id(url_or_id)
    res = engine.request.get(WebmasterRoute.video_embed_code(video_id))
    payload = res.json()
    return payload.get("embed", "") or payload.get("code", "")


def get_deleted_videos(engine: Engine, page: int = 1) -> Any:
    res = engine.request.get(WebmasterRoute.deleted_videos(page))
    return res.json()


def get_tags(engine: Engine, letter: str = "a") -> List[str]:
    res = engine.request.get(WebmasterRoute.tags(letter))
    payload = res.json()
    return payload.get("tags", [])


def get_categories(engine: Engine) -> Any:
    res = engine.request.get(WebmasterRoute.categories())
    return res.json()


def get_pornstars(engine: Engine) -> Any:
    res = engine.request.get(WebmasterRoute.stars())
    return res.json()


def get_pornstars_detail(engine: Engine) -> Any:
    res = engine.request.get(WebmasterRoute.stars_detailed())
    return res.json()
