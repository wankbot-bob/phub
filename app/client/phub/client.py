from __future__ import annotations

from typing import Any, Dict, Optional

from .apis import get_auto_complete, get_main_page, get_token, login, logout
from .engine import Engine
from .parsers import (
    album_page,
    album_search,
    channel_page,
    channel_search,
    gif_search,
    model_page,
    model_search,
    model_uploaded_videos,
    photo_page,
    pornstar_list,
    pornstar_page,
    pornstar_search,
    random_page,
    recommended,
    video_list,
    video_page,
    video_search,
)
from .webmaster import (
    get_categories,
    get_deleted_videos,
    get_pornstars,
    get_pornstars_detail,
    get_tags,
    get_video,
    get_video_embed_code,
    is_video_active,
    search as webmaster_search,
)


class WebMaster:
    def __init__(self, engine: Engine):
        self.engine = engine

    def search(self, keyword: str, **options: Any):
        return webmaster_search(self.engine, keyword, **options)

    def get_video(self, url_or_id: str, thumbsize: str = "large"):
        return get_video(self.engine, url_or_id, thumbsize)

    def is_video_active(self, url_or_id: str) -> bool:
        return is_video_active(self.engine, url_or_id)

    def get_video_embed_code(self, url_or_id: str) -> str:
        return get_video_embed_code(self.engine, url_or_id)

    def get_deleted_videos(self, page: int = 1):
        return get_deleted_videos(self.engine, page)

    def get_tags(self, letter: str = "a"):
        return get_tags(self.engine, letter)

    def get_categories(self):
        return get_categories(self.engine)

    def get_pornstars(self):
        return get_pornstars(self.engine)

    def get_pornstars_detail(self):
        return get_pornstars_detail(self.engine)


class PornHub:
    def __init__(self, dump_page: bool | str = False):
        self.engine = Engine(dump_page=dump_page)
        self.webMaster = WebMaster(self.engine)

    def set_agent(self, agent: Any) -> None:
        self.engine.request.set_agent(agent)

    def set_header(self, key: str, value: str) -> None:
        self.engine.request.set_header(key, value)

    def get_cookies(self) -> Dict[str, str]:
        return self.engine.request.get_cookies()

    def get_cookie(self, key: str) -> Optional[str]:
        return self.engine.request.get_cookie(key)

    def set_cookie(self, key: str, value: str) -> None:
        self.engine.request.set_cookie(key, value)

    def delete_cookie(self, key: str) -> None:
        self.engine.request.delete_cookie(key)

    def warmup(self):
        # Kept for API parity; request warmed up on first video call.
        return None

    def login(self, account: str, password: str):
        return login(self.engine, account, password)

    def logout(self):
        return logout(self.engine)

    def get_token(self):
        return get_token(self.engine)

    def video(self, url_or_id: str):
        if not self.engine.warmed_up:
            get_main_page(self.engine)
            self.engine.warmed_up = True
        return video_page(self.engine, url_or_id)

    def album(self, url_or_id: str):
        return album_page(self.engine, url_or_id)

    def photo(self, url_or_id: str):
        return photo_page(self.engine, url_or_id)

    def pornstar(self, url_or_name: str):
        return pornstar_page(self.engine, url_or_name)

    def model(self, url_or_name: str):
        return model_page(self.engine, url_or_name)

    def model_videos(self, url_or_name: str, page: int = 1):
        return model_uploaded_videos(self.engine, url_or_name, page)

    def channel(self, url_or_name: str):
        return channel_page(self.engine, url_or_name)

    def random_video(self):
        return random_page(self.engine)

    def auto_complete(self, keyword: str, **options: Any):
        return get_auto_complete(self.engine, keyword, **options)

    def search_album(self, keyword: str, **options: Any):
        return album_search(self.engine, keyword, **options)

    def search_gif(self, keyword: str, **options: Any):
        return gif_search(self.engine, keyword, **options)

    def search_channel(self, keyword: str, **options: Any):
        return channel_search(self.engine, keyword, **options)

    def search_pornstar(self, keyword: str, **options: Any):
        return pornstar_search(self.engine, keyword, **options)

    def search_model(self, keyword: str, **options: Any):
        return model_search(self.engine, keyword, **options)

    def search_video(self, keyword: str, **options: Any):
        return video_search(self.engine, keyword, **options)

    def video_list(self, **options: Any):
        return video_list(self.engine, **options)

    def pornstar_list(self, **options: Any):
        return pornstar_list(self.engine, **options)

    def recommended_videos(self, **options: Any):
        return recommended(self.engine, **options)

    # Aliases to mirror the original JS naming
    def getToken(self):
        return self.get_token()

    def randomVideo(self):
        return self.random_video()

    def autoComplete(self, keyword: str, **options: Any):
        return self.auto_complete(keyword, **options)

    def searchAlbum(self, keyword: str, **options: Any):
        return self.search_album(keyword, **options)

    def searchGif(self, keyword: str, **options: Any):
        return self.search_gif(keyword, **options)

    def searchChannel(self, keyword: str, **options: Any):
        return self.search_channel(keyword, **options)

    def searchPornstar(self, keyword: str, **options: Any):
        return self.search_pornstar(keyword, **options)

    def searchModel(self, keyword: str, **options: Any):
        return self.search_model(keyword, **options)

    def modelVideos(self, url_or_name: str, page: int = 1):
        return self.model_videos(url_or_name, page)

    def searchVideo(self, keyword: str, **options: Any):
        return self.search_video(keyword, **options)

    def videoList(self, **options: Any):
        return self.video_list(**options)

    def pornstarList(self, **options: Any):
        return self.pornstar_list(**options)

    def recommendedVideos(self, **options: Any):
        return self.recommended_videos(**options)
