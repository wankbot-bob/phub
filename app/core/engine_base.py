from __future__ import annotations

from typing import Callable, Dict, Optional, Protocol, TypeVar


class _RequestLike(Protocol):
    def set_header(self, key: str, value: str) -> None: ...

    def set_cookie(self, key: str, value: str) -> None: ...

    def get(self, url: str, **kwargs): ...


DumperFactory = Callable[[Optional[str]], object]
RequestFactory = Callable[[Optional[object]], _RequestLike]
ReqT = TypeVar("ReqT", bound=_RequestLike)


class BaseEngine:
    """
    Minimal configurable engine base that site clients can subclass/extend.
    """

    def __init__(
        self,
        base_url: str,
        *,
        request_factory: RequestFactory,
        dumper_factory: Optional[DumperFactory] = None,
        dump_page: bool | str = False,
        default_headers: Optional[Dict[str, str]] = None,
        default_cookies: Optional[Dict[str, str]] = None,
        warmup: bool = True,
    ):
        dumper_target = dump_page if isinstance(dump_page, str) else None
        dumper = dumper_factory(dumper_target) if dump_page and dumper_factory else None
        self.BASE_URL = base_url
        self.request: ReqT = request_factory(dumper)
        self.dumper = dumper
        self.warmed_up = False
        self._apply_defaults(default_headers=default_headers, default_cookies=default_cookies)
        if warmup:
            self._warmup_cookies()

    def _apply_defaults(self, default_headers: Optional[Dict[str, str]] = None, default_cookies: Optional[Dict[str, str]] = None) -> None:
        headers = {
            "Host": self.BASE_URL.replace("https://", "").replace("http://", ""),
            "Origin": self.BASE_URL,
            "Referer": f"{self.BASE_URL}/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
        }
        if default_headers:
            headers.update(default_headers)
        for k, v in headers.items():
            self.request.set_header(k, v)

        cookies = default_cookies or {}
        for k, v in cookies.items():
            self.request.set_cookie(k, v)

    def _warmup_cookies(self) -> None:
        if self.warmed_up:
            return
        try:
            self.request.get(self.BASE_URL + "/")
        except Exception:
            pass
        self.warmed_up = True


__all__ = ["BaseEngine"]
