from __future__ import annotations

from urllib.parse import urlencode

from .constants import BASE_URL
from .mappings import (
    ALBUM_ORDERING_MAP,
    CHANNEL_SEARCH_ORDERING_MAP,
    CHANNEL_SEARCH_PERIOD_MAP,
    COUNTRY_MAP,
    GIF_ORDERING_MAP,
    PORNSTAR_LIST_ORDERING_MAP,
    PORNSTAR_ORDERING_MAP,
    PORNSTAR_POPULAR_PERIOD_MAP,
    PORNSTAR_VIEWED_PERIOD_MAP,
    RECOMMENDED_ORDERING_MAP,
    VIDEO_LIST_ORDERING_MAP,
    VIDEO_ORDERING_MAP,
    VIDEO_SEARCH_PERIOD_MAP,
)
from .utils import dashify, searchify


def _build(path: str, params: dict | None = None) -> str:
    params = {k: v for k, v in (params or {}).items() if v not in (None, "", False)}
    query = urlencode(params, doseq=True)
    return f"{BASE_URL}{path}" + (f"?{query}" if query else "")


class Route:
    @staticmethod
    def main_page() -> str:
        return _build("/")

    @staticmethod
    def authenticate() -> str:
        return _build("/front/authenticate")

    @staticmethod
    def logout(token: str) -> str:
        return _build("/user/logout", {"token": token})

    @staticmethod
    def autocomplete(keyword: str, *, token: str, sexual_orientation: str = "straight") -> str:
        return _build(
            "/video/search_autocomplete",
            {
                "q": keyword,
                "orientation": sexual_orientation,
                "pornstars": "1",
                "token": token,
                "alt": 0,
            },
        )

    @staticmethod
    def album_page(album_id: str) -> str:
        return _build(f"/album/{album_id}")

    @staticmethod
    def photo_page(photo_id: str) -> str:
        return _build(f"/photo/{photo_id}")

    @staticmethod
    def video_page(video_id: str) -> str:
        return _build("/view_video.php", {"viewkey": video_id})

    @staticmethod
    def pornstar_page(name: str) -> str:
        return _build(f"/pornstar/{name}")

    @staticmethod
    def model_page(name: str) -> str:
        return _build(f"/model/{name}")

    @staticmethod
    def model_videos_page(name: str, page: int) -> str:
        return _build(f"/model/{name}/videos", {"page": page})

    @staticmethod
    def channel_page(name: str) -> str:
        return _build(f"/channels/{name}")

    @staticmethod
    def random_page() -> str:
        return _build("/random")

    @staticmethod
    def recommended_page(order: str = "Most Relevant", page: int = 1, sexual_orientation: str = "straight") -> str:
        orientation = None if sexual_orientation == "straight" else sexual_orientation
        path = f"/{orientation}/recommended" if orientation else "/recommended"
        return _build(
            path,
            {
                "o": RECOMMENDED_ORDERING_MAP.get(order, ""),
                "page": page if page != 1 else None,
            },
        )

    @staticmethod
    def album_search(keyword: str, *, page: int = 1, segments: str | list[str] = "female-straight-uncategorized", order: str = "Most Relevant", verified: bool = False) -> str:
        segment = dashify(segments)
        return _build(
            f"/albums/{segment}",
            {
                "search": searchify(keyword),
                "page": page if page != 1 else None,
                "o": ALBUM_ORDERING_MAP.get(order, ""),
                "verified": "1" if verified else None,
            },
        )

    @staticmethod
    def gif_search(keyword: str, *, page: int = 1, order: str = "Most Relevant", sexual_orientation: str = "straight") -> str:
        orientation = None if sexual_orientation == "straight" else sexual_orientation
        path = f"/{orientation}/gifs/search" if orientation else "/gifs/search"
        return _build(
            path,
            {
                "search": searchify(keyword),
                "page": page if page != 1 else None,
                "o": GIF_ORDERING_MAP.get(order, ""),
            },
        )

    @staticmethod
    def channel_search(keyword: str, *, page: int = 1, order: str = "Most Relevant", period: str | None = None) -> str:
        return _build(
            "/channels/search",
            {
                "channelSearch": searchify(keyword),
                "page": page if page != 1 else None,
                "o": CHANNEL_SEARCH_ORDERING_MAP.get(order, ""),
                "t": CHANNEL_SEARCH_PERIOD_MAP.get(period, None)
                if order == "Most Video Views" and period and period != "alltime"
                else None,
            },
        )

    @staticmethod
    def pornstar_search(keyword: str, *, page: int = 1, order: str = "Most Relevant", sexual_orientation: str = "straight") -> str:
        orientation = None if sexual_orientation == "straight" else sexual_orientation
        path = f"/{orientation}/pornstars/search" if orientation else "/pornstars/search"
        return _build(
            path,
            {
                "search": searchify(keyword),
                "page": page if page != 1 else None,
                "o": PORNSTAR_ORDERING_MAP.get(order, ""),
            },
        )

    @staticmethod
    def video_search(
        keyword: str,
        *,
        page: int = 1,
        order: str = "Most Relevant",
        hd: bool = False,
        production: str = "all",
        duration_min: int | None = None,
        duration_max: int | None = None,
        filter_category: int | None = None,
        exclude_category: str | None = None,
        sexual_orientation: str = "straight",
        period: str | None = None,
    ) -> str:
        orientation = None if sexual_orientation == "straight" else sexual_orientation
        path = f"/{orientation}/video/search" if orientation else "/video/search"
        return _build(
            path,
            {
                "search": searchify(keyword),
                "page": page if page != 1 else None,
                "o": VIDEO_ORDERING_MAP.get(order, ""),
                "hd": "1" if hd else None,
                "p": production if production != "all" else None,
                "min_duration": duration_min,
                "max_duration": duration_max,
                "filter_category": filter_category,
                "exclude_category": exclude_category,
                "t": VIDEO_SEARCH_PERIOD_MAP.get(period, None)
                if order in ("Most Viewed", "Top Rated") and period and period != "alltime"
                else None,
            },
        )

    @staticmethod
    def video_list(
        *,
        page: int = 1,
        order: str = "Featured Recently",
        hd: bool = False,
        production: str = "all",
        duration_min: int | None = None,
        duration_max: int | None = None,
        filter_category: int | None = None,
        sexual_orientation: str = "straight",
        period: str | None = None,
        country: str | None = None,
    ) -> str:
        if sexual_orientation == "transgender":
            path = "/transgender"
        elif sexual_orientation == "gay":
            path = "/gayporn"
        else:
            path = "/video"
        return _build(
            path,
            {
                "c": filter_category,
                "p": production if production != "all" else None,
                "o": VIDEO_LIST_ORDERING_MAP.get(order, ""),
                "t": VIDEO_SEARCH_PERIOD_MAP.get(period, None)
                if order in ("Most Viewed", "Top Rated") and period and period != "alltime"
                else None,
                "cc": COUNTRY_MAP.get(country, None)
                if order == "Hottest" and country and country != "World"
                else None,
                "min_duration": duration_min,
                "max_duration": duration_max,
                "hd": "1" if hd else None,
                "page": page if page != 1 else None,
            },
        )

    @staticmethod
    def pornstar_list(
        *,
        gay: bool = False,
        performer_type: str | None = None,
        gender: str | None = None,
        ethnicity: str | None = None,
        tattoos: bool | None = None,
        cup: str | None = None,
        piercings: bool | None = None,
        hair: str | None = None,
        breast_type: str | None = None,
        age_from: int = 18,
        age_to: int = 99,
        order: str = "Most Popular",
        page: int = 1,
        letter: str | None = None,
        time_range: str | None = None,
    ) -> str:
        def yes_no(val: Optional[bool]) -> Optional[str]:
            if val is None:
                return None
            return "yes" if val else "no"

        path = "/gay/pornstars" if gay else "/pornstars"
        return _build(
            path,
            {
                "performerType": performer_type,
                "gender": gender,
                "ethnicity": ethnicity,
                "piercings": yes_no(piercings),
                "age": f"{age_from}-{age_to}" if f"{age_from}-{age_to}" != "18-99" else None,
                "cup": cup.lower() if cup else None,
                "breastType": breast_type,
                "hair": hair,
                "tattoos": yes_no(tattoos),
                "o": PORNSTAR_LIST_ORDERING_MAP.get(order, ""),
                "letter": letter.lower()
                if order == "Alphabetical"
                else None,
                "timeRange": PORNSTAR_POPULAR_PERIOD_MAP.get(time_range, None)
                if order == "Most Popular" and time_range and time_range != "monthly"
                else PORNSTAR_VIEWED_PERIOD_MAP.get(time_range, None)
                if order == "Most Viewed" and time_range and time_range != "alltime"
                else None,
                "page": page if page != 1 else None,
            },
        )


WEBMASTER_BASE = "/webmasters"


class WebmasterRoute:
    @staticmethod
    def is_video_active(video_id: str) -> str:
        return _build(f"{WEBMASTER_BASE}/is_video_active", {"id": video_id})

    @staticmethod
    def categories() -> str:
        return _build(f"{WEBMASTER_BASE}/categories")

    @staticmethod
    def deleted_videos(page: int) -> str:
        return _build(f"{WEBMASTER_BASE}/deleted_videos", {"page": page})

    @staticmethod
    def video_embed_code(video_id: str) -> str:
        return _build(f"{WEBMASTER_BASE}/video_embed_code", {"id": video_id})

    @staticmethod
    def stars_detailed() -> str:
        return _build(f"{WEBMASTER_BASE}/stars_detailed")

    @staticmethod
    def stars() -> str:
        return _build(f"{WEBMASTER_BASE}/stars")

    @staticmethod
    def tags(letter: str) -> str:
        return _build(f"{WEBMASTER_BASE}/tags", {"list": letter})

    @staticmethod
    def video_by_id(video_id: str, thumbsize: str) -> str:
        return _build(f"{WEBMASTER_BASE}/video_by_id", {"id": video_id, "thumbsize": thumbsize})

    @staticmethod
    def search(keyword: str, *, page: int | None = None, period: str | None = None, ordering: str | None = None, thumbsize: str | None = None, tags: list[str] | None = None, stars: list[str] | None = None, category: list[str] | None = None) -> str:
        return _build(
            f"{WEBMASTER_BASE}/search",
            {
                "search": "+".join(keyword.split()),
                "page": page,
                "period": period,
                "ordering": ordering,
                "thumbsize": thumbsize,
                "tags[]": ",".join(tags) if tags else None,
                "stars[]": ",".join(stars) if stars else None,
                "category": ",".join(category) if category else None,
            },
        )
