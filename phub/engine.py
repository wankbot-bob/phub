from __future__ import annotations

from .constants import BASE_URL
from .http import Dumper, Request


class Engine:
    def __init__(self, dump_page: bool | str = False):
        dumper_target = dump_page if isinstance(dump_page, str) else None
        dumper = Dumper(dumper_target) if dump_page else None
        self.BASE_URL = BASE_URL
        self.request = Request(dumper)
        self.dumper = dumper
        self.warmed_up = False
        self._apply_defaults()

    def _apply_defaults(self) -> None:
        self.request.set_header("Host", self.BASE_URL.replace("https://", ""))
        self.request.set_header("Origin", self.BASE_URL)
        self.request.set_header("Referer", f"{self.BASE_URL}/")
        self.request.set_header(
            "User-Agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
        )

        # Mimic the cookie setup from the original JS client to skip interstitials.
        self.request.set_cookie("platform", "pc")
        self.request.set_cookie("accessAgeDisclaimerPH", "1")
        self.request.set_cookie("accessAgeDisclaimerUK", "1")
        self.request.set_cookie("accessPH", "1")
        self.request.set_cookie("age_verified", "1")
        self.request.set_cookie("atatusScript", "hide")
        self.request.set_cookie("cookiesBannerSeen", "1")
        self.request.set_cookie("hasVisited", "1")
