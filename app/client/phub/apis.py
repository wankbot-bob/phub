from __future__ import annotations

import re
from typing import Any, Dict

from .engine import Engine
from .routes import Route
from .utils import get_data, get_soup


def get_main_page(engine: Engine) -> str:
    response = engine.request.get(Route.main_page())
    return response.text


def get_token(engine: Engine) -> str:
    html = get_main_page(engine)
    soup = get_soup(html)
    input_el = soup.select_one('form#search_form input[name="search"]')
    token = get_data(input_el, "token")
    if not token:
        raise RuntimeError("Failed to obtain search token from Pornhub main page")
    return token


def _extract_login_token(html: str) -> tuple[str, str]:
    soup = get_soup(html)
    token_el = soup.select_one('[name="token"]') if hasattr(soup, "select_one") else None
    redirect_el = soup.select_one('[name="redirect"]') if hasattr(soup, "select_one") else None
    token = str(token_el.get("value", "") or "") if token_el else ""
    redirect = str(redirect_el.get("value", "") or "") if redirect_el else ""
    return token, redirect


def login(engine: Engine, account: str, password: str) -> Dict[str, Any]:
    if not account or not isinstance(account, str):
        raise ValueError("Invalid account")
    if not password or not isinstance(password, str):
        raise ValueError("Invalid password")

    html = get_main_page(engine)
    token, redirect = _extract_login_token(html)
    payload = {
        "redirect": redirect,
        "token": token,
        "remember_me": 1,
        "from": "pc_login_modal_:show",
        "username": account,
        "password": password,
        "setSendTip": False,
    }
    res = engine.request.post_form(Route.authenticate(), payload)
    result = res.json()
    if result.get("success"):
        return {"success": True, "message": "Successfully logged in.", "premium": result.get("premium_redirect_cookie") == "1"}
    return {"success": False, "message": f"Login fail, Reason: {result.get('message', 'unknown')}", "premium": False}


def logout(engine: Engine) -> Dict[str, Any]:
    html = get_main_page(engine)
    match = re.search(r'href="/user/logout\?token=([a-zA-Z0-9-_.]*?)"', html)
    if not match:
        raise RuntimeError("Logout failed")
    token = match.group(1)
    engine.request.get(Route.logout(token))
    return {"success": True, "message": "Successfully logged out"}


def get_auto_complete(engine: Engine, keyword: str, *, token: str | None = None, sexual_orientation: str = "straight") -> Dict[str, Any]:
    token = token or get_token(engine)
    response = engine.request.get(
        Route.autocomplete(keyword, token=token, sexual_orientation=sexual_orientation)
    )
    result = response.json()

    models = [
        {**item, "url": Route.model_page(item["slug"])}
        for item in result.get("models", []) or []
    ]
    pornstars = [
        {**item, "url": Route.pornstar_page(item["slug"])}
        for item in result.get("pornstars", []) or []
    ]
    channels = [
        {**item, "url": Route.channel_page(item["slug"])}
        for item in result.get("channels", []) or []
    ]

    models.sort(key=lambda x: x.get("rank", 0))
    pornstars.sort(key=lambda x: x.get("rank", 0))
    channels.sort(key=lambda x: x.get("rank", ""))

    return {
        "queries": result.get("queries", []),
        "albums": result.get("albums", []),
        "models": models,
        "pornstars": pornstars,
        "channels": channels,
        "isDdBannedWord": str(result.get("isDdBannedWord", "false")).lower() == "true",
        "popularSearches": result.get("popularSearches", []),
    }
