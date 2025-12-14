from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests
from requests import Response

from .errors import HttpStatusError, IllegalError
from .utils import get_soup


class Dumper:
    def __init__(self, target: Optional[str] = None):
        base = Path(target) if target else Path.cwd() / "_dump"
        base.mkdir(parents=True, exist_ok=True)
        self.base = base

    def _normalize_path(self, url: str) -> str:
        parsed = urlparse(url)
        normalized = parsed.path.rstrip("/").replace("/", "_") or "index"
        return f"{int(time.time() * 1000)}_{normalized}"

    def capture(self, response: Response) -> None:
        content_type = response.headers.get("content-type", "")
        normalized = self._normalize_path(response.url)
        suffix = "json" if "application/json" in content_type else "html"
        path = self.base / f"{normalized}.{suffix}"
        try:
            if suffix == "json":
                payload = response.json()
                path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            else:
                path.write_text(response.text, encoding="utf-8")
        except Exception:
            # Best-effort only
            return


class Request:
    def __init__(self, dumper: Optional[Dumper] = None):
        self.session = requests.Session()
        self._headers: Dict[str, str] = {}
        self._dumper = dumper

    def set_agent(self, agent: Any) -> None:
        """
        Attach a transport adapter or proxies dict.
        Adapter example: HTTPAdapter(pool_maxsize=20)
        Proxies example: {'https': 'http://proxy:8080'}
        """
        if isinstance(agent, requests.adapters.HTTPAdapter):
            self.session.mount("http://", agent)
            self.session.mount("https://", agent)
        elif isinstance(agent, dict):
            self.session.proxies.update(agent)
        else:
            # Fallback: let callers pass through request kwargs instead.
            self._headers["User-Agent"] = str(agent)

    def set_header(self, key: str, value: str) -> None:
        if key.lower() == "cookie":
            return
        self._headers[key] = value

    def get_cookies(self) -> Dict[str, str]:
        return {c.name: c.value for c in self.session.cookies}

    def get_cookie(self, key: str) -> Optional[str]:
        return self.session.cookies.get(key)

    def set_cookie(self, key: str, value: str) -> None:
        self.session.cookies.set(key, value)

    def delete_cookie(self, key: str) -> None:
        if key in self.session.cookies:
            del self.session.cookies[key]

    def _check_status(self, response: Response) -> None:
        if response.ok:
            return

        if response.status_code == 404:
            html = ""
            try:
                html = response.text
                if "deterrenceWarn" in html:
                    soup = get_soup(html)
                    warn = soup.select_one(".deterrenceWarn")
                    if warn and warn.get_text(strip=True):
                        raise IllegalError(warn.get_text(strip=True))
            except IllegalError:
                raise
            except Exception:
                pass
        raise HttpStatusError(f"{response.status_code} {response.reason} at {response.url}")

    def fetch(self, url: str, method: str = "GET", **kwargs: Any) -> Response:
        headers = {**self._headers, **kwargs.pop("headers", {})}
        allow_redirects = kwargs.pop("follow", True)
        response = self.session.request(
            method=method,
            url=url,
            headers=headers,
            allow_redirects=bool(allow_redirects),
            **kwargs,
        )
        self._check_status(response)

        if self._dumper:
            try:
                self._dumper.capture(response)
            except Exception:
                pass

        return response

    def get(self, url: str, **kwargs: Any) -> Response:
        return self.fetch(url, method="GET", **kwargs)

    def post(self, url: str, data: Any, **kwargs: Any) -> Response:
        return self.fetch(url, method="POST", json=data, **kwargs)

    def post_form(self, url: str, data: Dict[str, Any], **kwargs: Any) -> Response:
        return self.fetch(url, method="POST", data=data, **kwargs)
