from __future__ import annotations

from .constants import BASE_URL
from .http import Dumper, Request


class Engine:
    def __init__(self, dump_page: bool | str = False, base_url: str = BASE_URL, default_headers: dict | None = None, default_cookies: dict | None = None):
        dumper_target = dump_page if isinstance(dump_page, str) else None
        dumper = Dumper(dumper_target) if dump_page else None
        self.BASE_URL = base_url
        self.request = Request(dumper)
        self.dumper = dumper
        self.warmed_up = False
        self._apply_defaults(default_headers=default_headers, default_cookies=default_cookies)
        self._warmup_cookies()

    def _apply_defaults(self, default_headers: dict | None = None, default_cookies: dict | None = None) -> None:
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

        cookies = {
            "platform": "pc",
            "accessAgeDisclaimerPH": "1",
            "accessAgeDisclaimerUK": "1",
            "accessPH": "1",
            "age_verified": "1",
            "atatusScript": "hide",
            "cookiesBannerSeen": "1",
            "hasVisited": "1",
        }
        if default_cookies:
            cookies.update(default_cookies)
        for k, v in cookies.items():
            self.request.set_cookie(k, v)

    def _warmup_cookies(self) -> None:
        """
        Perform a single warmup GET to establish cookies and avoid deterrence redirects.
        This is invoked once per Engine instance.
        """
        if self.warmed_up:
            return
        try:
            self.request.get(self.BASE_URL + "/")
        except Exception:
            pass
        self.warmed_up = True
