from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Tuple
from urllib.parse import urljoin

from .apis import get_auto_complete
from .constants import BASE_URL
from .engine import Engine
from .routes import Route
from .urls import UrlParser
from .utils import (
    get_attr,
    get_data,
    get_soup,
    parse_readable_number,
    remove_comma,
    remove_protection_bracket,
    text_or_empty,
    to_hhmmss,
)


def parse_paging(soup) -> Dict[str, Any]:
    current_el = soup.select_one("li.page_current")
    current = int(current_el.get_text() or 1) if current_el else 1
    next_page = soup.select_one("li.page_next")
    is_end = not next_page or "disabled" in (next_page.get("class") or [])
    max_page = current
    if not is_end:
        prev = next_page.find_previous("li")
        try:
            max_page = int(prev.get_text())
        except Exception:
            max_page = current
    return {"current": current, "maxPage": max_page, "isEnd": is_end}


def parse_counting(soup) -> Dict[str, int]:
    try:
        counter_text = text_or_empty(soup.select_one(".showingCounter"))
        match = re.search(r"(\d+)-(\d+)\s+of\s+(\d+)", counter_text)
        if not match:
            return {"from": 0, "to": 0, "total": 0}
        return {"from": int(match.group(1)), "to": int(match.group(2)), "total": int(match.group(3))}
    except Exception:
        return {"from": 0, "to": 0, "total": 0}


def parse_media_definitions(html: str) -> List[Dict[str, Any]]:
    pattern = re.compile(
        r'{(?:"group":\d+,"height":\d+,"width":\d+,)?'
        r'"defaultQuality":(?P<default>true|false|\d+),'
        r'"format":"(?P<format>\w+)",'
        r'"videoUrl":"(?P<videoUrl>.+?)",'
        r'"quality":(?P<quality>"\d+"|\d+|\[[\d,]*\])'
        r'(?:,"remote":(?P<remote>true|false))?}'
    )
    results: List[Dict[str, Any]] = []
    for match in pattern.finditer(html):
        try:
            default_raw = match.group("default")
            if default_raw == "true":
                default_quality: bool | int = True
            elif default_raw == "false":
                default_quality = False
            else:
                default_quality = int(default_raw)

            video_url = match.group("videoUrl").replace("\\", "")
            quality_raw = match.group("quality")
            if quality_raw.startswith("["):
                quality = json.loads(quality_raw)
            else:
                quality = int(quality_raw.replace('"', ""))
            remote = match.group("remote") == "true"

            results.append(
                {
                    "defaultQuality": default_quality,
                    "format": match.group("format"),
                    "videoUrl": video_url,
                    "quality": quality,
                    "remote": remote,
                }
            )
        except Exception:
            continue
    return results


def parse_video_result(soup, container: Any) -> List[Dict[str, Any]]:
    if isinstance(container, str):
        elements = soup.select(f"{container} li.videoblock")
    else:
        elements = container.select("li.videoblock")
    results: List[Dict[str, Any]] = []
    for el in elements:
        thumb = el.select_one(".linkVideoThumb")
        title = get_attr(thumb, "title", "") or ""
        path = get_attr(thumb, "href", "") or ""
        if path == "javascript:void(0)":
            continue
        url = urljoin(BASE_URL, path)
        video_id = UrlParser.get_video_id(url)
        img = el.select_one("img")
        preview = get_attr(img, "src", "") or ""
        results.append(
            {
                "title": title,
                "id": video_id,
                "url": url,
                "views": text_or_empty(el.select_one(".views var")),
                "duration": text_or_empty(el.select_one(".duration")),
                "hd": bool(el.select_one(".hd-thumbnail")),
                "premium": bool(el.select_one(".premiumIcon")),
                "freePremium": bool(el.select_one(".marker-overlays .phpFreeBlock")),
                "preview": preview,
            }
        )
    return results


def video_page(engine: Engine, url_or_id: str) -> Dict[str, Any]:
    video_id = UrlParser.get_video_id(url_or_id)
    url = Route.video_page(video_id)
    res = engine.request.get(url)
    html = res.text
    soup = get_soup(html)
    return {"id": video_id, "url": url, "mediaDefinitions": parse_media_definitions(html), **_parse_video_dom(html, soup)}


def _parse_video_dom(html: str, soup):
    vote_up = parse_readable_number(text_or_empty(soup.select_one("span.votesUp")) or "0")
    vote_down = parse_readable_number(text_or_empty(soup.select_one("span.votesDown")) or "0")
    title = text_or_empty(soup.select_one("head > title")).replace(" - Pornhub.com", "")
    views_text = text_or_empty(soup.select_one("span.count")) or "0"
    views = parse_readable_number(views_text)
    total_vote = vote_up + vote_down
    vote = {
        "up": vote_up,
        "down": vote_down,
        "total": total_vote,
        "rating": 0 if total_vote == 0 else round(vote_up / total_vote, 2),
    }
    premium = bool(soup.select_one("#videoTitle .ph-icon-badge-premium"))
    thumb = get_attr(soup.select_one(".thumbnail img"), "src", "") or ""
    preview = get_attr(soup.select_one('head meta[property="og:image"]'), "content", "") or ""

    provider_link = soup.select_one(".usernameBadgesWrapper a.bolded")
    provider = (
        {"username": text_or_empty(provider_link), "url": get_attr(provider_link, "href", "")}
        if provider_link
        else None
    )

    traffic_meta = soup.select_one("head meta[name=adsbytrafficjunkycontext]")
    tags = (get_data(traffic_meta, "context-tag", "") or "").split(",") if traffic_meta else []
    pornstars = (get_data(traffic_meta, "context-pornstar", "") or "").split(",") if traffic_meta else []
    categories = (get_data(traffic_meta, "context-category", "") or "").split(",") if traffic_meta else []

    duration_meta = soup.select_one('head meta[property="video:duration"]')
    try:
        duration = int(get_attr(duration_meta, "content", 0) or 0)
    except Exception:
        duration = 0
    duration_formatted = to_hhmmss(duration)
    upload_date = _parse_ld_json(soup)

    return {
        "title": title,
        "views": views,
        "vote": vote,
        "premium": premium,
        "thumb": thumb,
        "preview": preview,
        "videos": [],
        "provider": provider,
        "tags": [t for t in tags if t],
        "pornstars": [p for p in pornstars if p],
        "categories": [c for c in categories if c],
        "duration": duration,
        "durationFormatted": duration_formatted,
        "uploadDate": upload_date,
    }


def _parse_ld_json(soup) -> Any:
    try:
        ld = soup.select_one('head script[type="application/ld+json"]')
        if not ld:
            return None
        payload = json.loads(ld.get_text())
        return payload.get("uploadDate")
    except Exception:
        return None


def random_page(engine: Engine) -> Dict[str, Any]:
    response = engine.request.fetch(Route.random_page())
    redirected = response.url
    video_id = UrlParser.get_video_id(redirected)
    html = response.text
    soup = get_soup(html)
    return {"id": video_id, "url": Route.video_page(video_id), "mediaDefinitions": parse_media_definitions(html), **_parse_video_dom(html, soup)}


def album_page(engine: Engine, url_or_id: str) -> Dict[str, Any]:
    album_id = UrlParser.get_album_id(url_or_id)
    url = Route.album_page(album_id)
    res = engine.request.get(url)
    html = res.text
    soup = get_soup(html)
    return {
        "title": text_or_empty(soup.select_one("h1.photoAlbumTitleV2")),
        "photos": _parse_album_photos(soup),
        "provider": _parse_album_provider(soup),
        "tags": _parse_tag(soup),
    }


def _parse_album_photos(soup) -> List[Dict[str, Any]]:
    items = soup.select("ul.photosAlbumsListing li.photoAlbumListContainer div.photoAlbumListBlock")
    photos = []
    for item in items:
        path = get_attr(item.find("a"), "href", "") or ""
        url = f"{BASE_URL}{path}" if path else ""
        views = text_or_empty(item.select_one(".album-views")).replace("Views: ", "").strip()
        rating = text_or_empty(item.select_one(".album-rating"))
        preview = get_data(item, "bkg", "") or ""
        if not preview:
            style = get_attr(item, "style", "")
            match = re.search(r'url\("(.+)"\)', style or "")
            preview = match.group(1) if match else ""
        photos.append({"url": url, "views": views, "rating": rating, "preview": preview})
    return photos


def _parse_album_provider(soup) -> Dict[str, Any]:
    user = soup.select_one("div.pfileInfoBox div.usernameWrap")
    return {
        "id": get_data(user, "userid", ""),
        "username": text_or_empty(user.select_one("a")),
        "url": get_attr(user.select_one("a"), "href", "") or "",
    }


def _parse_tag(soup) -> List[str]:
    return [text_or_empty(el) for el in soup.select("div.tagContainer > a") if text_or_empty(el)]


def photo_page(engine: Engine, url_or_id: str) -> Dict[str, Any]:
    photo_id = UrlParser.get_photo_id(url_or_id)
    url = Route.photo_page(photo_id)
    res = engine.request.get(url)
    html = res.text
    soup = get_soup(html)
    return {"info": _parse_photo_info(soup), "provider": _parse_photo_provider(soup), "tags": _parse_photo_tags(soup)}


def _parse_photo_info(soup) -> Dict[str, Any]:
    wrapper = soup.select_one("div#photoWrapper")
    img = wrapper.find("img") if wrapper else None
    title = get_attr(img, "alt", "") if img else ""
    src = get_attr(img, "src", "") if img else ""
    album_id = str(get_data(wrapper, "album-id", "")) if wrapper else ""
    rating = f"{text_or_empty(soup.select_one('span#votePercentageNumber'))}%"
    views_text = text_or_empty(soup.select_one("section#photoInfoSection strong"))
    views = int(remove_comma(views_text) or "0") if views_text else 0
    return {"title": title, "views": views, "rating": rating, "albumID": album_id, "url": src}


def _parse_photo_provider(soup) -> Dict[str, Any]:
    user = soup.select_one("div#userInformation div.usernameWrap")
    return {
        "id": get_data(user, "userid", 0) or 0,
        "username": text_or_empty(user.select_one("a")),
        "url": get_attr(user.select_one("a"), "href", "") or "",
    }


def _parse_photo_tags(soup) -> List[str]:
    return [el.get_text() for el in soup.select("ul.tagList a.tagText")]


def pornstar_page(engine: Engine, url_or_name: str) -> Dict[str, Any]:
    name = UrlParser.get_pornstar_name(url_or_name)
    if not name:
        raise ValueError(f"Invalid pornstar input: {url_or_name}")
    url = Route.pornstar_page(name)
    res = engine.request.get(url)
    html = res.text
    soup = get_soup(html)
    return _parse_profile_page(soup, is_model=False)


def model_page(engine: Engine, url_or_name: str) -> Dict[str, Any]:
    name = UrlParser.get_model_name(url_or_name)
    if not name:
        raise ValueError(f"Invalid model input: {url_or_name}")
    url = Route.model_page(name)
    res = engine.request.get(url)
    html = res.text
    soup = get_soup(html)
    return _parse_profile_page(soup, is_model=True)


def model_uploaded_videos(engine: Engine, url_or_name: str, page: int = 1) -> Dict[str, Any]:
    name = UrlParser.get_model_name(url_or_name)
    if not name:
        raise ValueError(f"Invalid model input: {url_or_name}")
    url = Route.model_videos_page(name, page or 1)
    res = engine.request.get(url)
    soup = get_soup(res.text)
    return {"data": parse_video_result(soup, ".videoUList"), "paging": parse_paging(soup), "counting": parse_counting(soup)}


def _parse_profile_page(soup, is_model: bool) -> Dict[str, Any]:
    default_mapper = {"key": lambda k: k, "value": lambda v: v}
    yes_no = lambda v: v.strip() == "Yes"
    squeeze = lambda v: " ".join(v.split())
    num_mapper = lambda v: parse_readable_number(v)

    key_mapper = {
        "Relationship status": {"key": lambda _: "relationship", "value": default_mapper["value"]},
        "Interested in": {"key": lambda _: "interestedIn", "value": default_mapper["value"]},
        "Gender": {"key": lambda _: "gender", "value": default_mapper["value"]},
        "Height": {"key": lambda _: "height", "value": default_mapper["value"]},
        "Weight": {"key": lambda _: "weight", "value": default_mapper["value"]},
        "Ethnicity": {"key": lambda _: "ethnicity", "value": default_mapper["value"]},
        "Background": {"key": lambda _: "background", "value": default_mapper["value"]},
        "Hair Color": {"key": lambda _: "hairColor", "value": default_mapper["value"]},
        "Eye Color": {"key": lambda _: "eyeColor", "value": default_mapper["value"]},
        "Fake Boobs": {"key": lambda _: "fakeBoobs", "value": yes_no},
        "Tattoos": {"key": lambda _: "tattoos", "value": yes_no},
        "Piercings": {"key": lambda _: "piercings", "value": yes_no},
        "Video Views": {"key": lambda _: "videoViews", "value": num_mapper},
        "Profile Views": {"key": lambda _: "profileViews", "value": num_mapper},
        "Pornstar Profile Views": {"key": lambda _: "pornstarProfileViews", "value": num_mapper},
        "Videos Watched": {"key": lambda _: "videoWatched", "value": num_mapper},
        "Turn Ons": {"key": lambda _: "turnOns", "value": default_mapper["value"]},
        "Turn Offs": {"key": lambda _: "turnOffs", "value": default_mapper["value"]},
        "Interests and hobbies": {"key": lambda _: "interests", "value": default_mapper["value"]},
        "Born": {"key": lambda _: "born", "value": default_mapper["value"]},
        "Birth Place": {"key": lambda _: "birthPlace", "value": default_mapper["value"]},
        "Birthplace": {"key": lambda _: "birthPlace", "value": default_mapper["value"]},
        "Star Sign": {"key": lambda _: "starSign", "value": default_mapper["value"]},
        "Measurements": {"key": lambda _: "measurements", "value": default_mapper["value"]},
        "City and Country": {"key": lambda _: "cityAndCountry", "value": default_mapper["value"]},
        "Endowment": {"key": lambda _: "endowment", "value": default_mapper["value"]},
        "Career Status": {"key": lambda _: "careerStatus", "value": default_mapper["value"]},
        "Career Start and End": {"key": lambda _: "careerStartAndEnd", "value": squeeze},
    }

    info = {}
    for block in soup.select("div.infoPiece"):
        key_el = block.select_one("span:nth-child(1)")
        value_el = block.select_one("span:nth-child(2)")
        key_text = text_or_empty(key_el).replace(":", "")
        value_text = text_or_empty(value_el) or block.get_text(strip=True).replace(text_or_empty(key_el), "").strip()
        mapper = key_mapper.get(key_text, default_mapper)
        info[mapper["key"](key_text)] = mapper["value"](value_text)

    name = text_or_empty(soup.select_one(".nameSubscribe > .name"))
    rank = parse_readable_number(text_or_empty(soup.select_one("div.rankingInfo > .infoBox > span")))
    avatar = get_attr(soup.select_one("img#getAvatar, .topProfileHeader > .thumbImage > img"), "src", "") or ""
    cover = get_attr(soup.select_one("img#coverPictureDefault, .topProfileHeader > .coverImage > img"), "src", "") or ""
    about = text_or_empty(soup.select_one("section.aboutMeSection > div:nth-child(2)"))
    bio_el = soup.select_one('.biographyText .content div[itemprop="description"], .bio:not(:has(.aboutMeSection)) > .text')
    bio = " ".join(text_or_empty(bio_el).split())
    verified = bool(soup.select_one(".badge-username > .verifiedPornstar"))
    awarded = bool(soup.select_one(".badge-username > .trophyPornStar"))
    premium = bool(soup.select_one(".badge-username > .premium-icon"))

    sub_el = soup.select_one('div.tooltipTrig.infoBox[data-title^="Subscribers:"]')
    subscribers_text = get_data(sub_el, "title", "") or ""
    subscribers_text = subscribers_text.replace("Subscribers: ", "")
    subscribers_text2 = text_or_empty(soup.select_one('div.infoBox:has(.title:-soup-contains("Subscribers")) > span'))
    subscribers = parse_readable_number(subscribers_text) or parse_readable_number(subscribers_text2)

    featured_in = []
    for el in soup.select("div.featuredIn > a"):
        title = text_or_empty(el)
        href = get_attr(el, "href", "") or ""
        if title and href:
            featured_in.append({"name": title, "url": href})

    uploaded_video_el = None
    tagged_video_el = None
    uploaded_video_count = 0
    tagged_video_count = 0
    if verified:
        uploaded_video_el = soup.select_one(".pornstarUploadedVideos, .mostRecentPornstarVideos")
        uploaded_video_count = _parse_video_count(text_or_empty(soup.select_one(".pornstarUploadedVideos .pornstarVideosCounter")))
        tagged_video_el = soup.select_one(".mostRecentPornstarVideos")
        tagged_video_count = _parse_video_count(text_or_empty(soup.select_one(".mostRecentPornstarVideos .pornstarVideosCounter")))
    else:
        counter_el = soup.select_one(".pornstarVideosCounter")
        if counter_el:
            title = text_or_empty(counter_el.parent().select_one(".sectionTitle > h2"))
            if title.endswith("Tagged Videos"):
                tagged_video_el = counter_el.parent()
                tagged_video_count = _parse_video_count(text_or_empty(counter_el))

    socials = {
        "website": get_attr(soup.select_one(".socialList a:has(.officialSiteIcon)"), "href"),
        "twitter": get_attr(soup.select_one(".socialList a:has(.ph-icon-twitterX)"), "href"),
        "instagram": get_attr(soup.select_one(".socialList a:has(.instagramIcon)"), "href"),
        "snapchat": get_attr(soup.select_one(".socialList a:has(.snapchatIcon)"), "href"),
        "modelhub": get_attr(soup.select_one(".socialList a:has(.modelhubIcon)"), "href"),
        "amazonWishList": get_attr(
            soup.select_one(".socialList a:has(.amazonWishlistIcon), .socialList a:has(.amazonWLIcon)"), "href"
        ),
    }

    uploaded_videos = parse_video_result(soup, uploaded_video_el) if uploaded_video_el else []
    most_recent_videos = parse_video_result(soup, tagged_video_el) if tagged_video_el else []

    base = {
        "name": name,
        "about": about,
        "bio": bio,
        "avatar": avatar,
        "cover": cover,
        "rank": rank,
        "verified": verified,
        "awarded": awarded,
        "premium": premium,
        "subscribers": subscribers,
        "featuredIn": featured_in,
        "uploadedVideoCount": uploaded_video_count,
        "taggedVideoCount": tagged_video_count,
        "socials": socials,
        "mostRecentVideos": most_recent_videos,
    }
    if not is_model:
        base["uploadedVideos"] = uploaded_videos
    else:
        base["uploadedVideos"] = uploaded_videos
    base.update(info)
    return base


def _parse_video_count(text: str) -> int:
    if not text:
        return 0
    match = re.search(r"Showing \d+-\d+ of (\d+)", text)
    if match:
        return parse_readable_number(match.group(1))
    return 0


def channel_page(engine: Engine, url_or_name: str) -> Dict[str, Any]:
    name = UrlParser.get_channel_name(url_or_name)
    if not name:
        raise ValueError(f"Invalid channel input: {url_or_name}")
    url = Route.channel_page(name)
    res = engine.request.get(url)
    soup = get_soup(res.text)
    return _parse_channel_dom(soup, url)


def _parse_channel_dom(soup, url: str) -> Dict[str, Any]:
    name = text_or_empty(soup.select_one(".bottomExtendedWrapper .title"))
    description_el = soup.select_one("#channelsBody .cdescriptions")
    about_candidate = description_el.contents[0] if description_el and description_el.contents else None
    about = about_candidate.strip() if isinstance(about_candidate, str) else None
    avatar = get_attr(soup.select_one("img#getAvatar"), "src", "") or ""
    cover = get_attr(soup.select_one("img#coverPictureDefault"), "src", "") or ""

    stats = {}
    for info in soup.select("#stats .info"):
        key = text_or_empty(info.select_one("span")).upper()
        value = text_or_empty(info).replace(key, "").strip()
        mapper = {
            "RANK": ("rank", parse_readable_number),
            "VIDEOS": ("videoCount", parse_readable_number),
            "VIDEO VIEWS": ("videoViews", parse_readable_number),
            "SUBSCRIBERS": ("subscribers", parse_readable_number),
        }.get(key)
        if mapper:
            stats[mapper[0]] = mapper[1](value)

    videos = parse_video_result(soup, ".videoUList")
    pornstars = parse_pornstar_result(soup, ".channelPornstars ")

    return {
        "name": name,
        "url": url,
        "avatar": avatar,
        "cover": cover,
        "about": about,
        **stats,
        "videos": videos,
        "pornstars": pornstars,
    }


def parse_pornstar_result(soup, container: str) -> List[Dict[str, Any]]:
    items = soup.select(f"{container} li.performerCard")
    results = []
    for item in items:
        name = text_or_empty(item.select_one(".performerCardName"))
        path = get_attr(item.select_one("a.title"), "href", "") or ""
        url = urljoin(BASE_URL, path)
        views = text_or_empty(item.select_one(".viewsNumber")).replace("Views", "").strip() or "0"
        video_num_text = text_or_empty(item.select_one(".videosNumber")).replace("Videos", "")
        video_num = int(video_num_text or 0) if video_num_text else 0
        rank_text = text_or_empty(item.select_one(".rank_number"))
        rank = int(rank_text or 0) if rank_text else 0
        img = item.select_one("img")
        photo = get_data(img, "thumb_url", "") or ""
        verified = bool(item.select_one(".verifiedPornstar"))
        awarded = bool(item.select_one(".trophyPornStar"))
        results.append(
            {
                "name": name,
                "url": url,
                "views": views,
                "videoNum": video_num,
                "rank": rank,
                "photo": photo,
                "verified": verified,
                "awarded": awarded,
            }
        )
    return results


def video_list(engine: Engine, **options: Any) -> Dict[str, Any]:
    url = Route.video_list(**options)
    res = engine.request.get(url)
    soup = get_soup(res.text)
    return {
        "data": parse_video_result(soup, "#videoCategory"),
        "paging": parse_paging(soup),
        "counting": parse_counting(soup),
    }


def pornstar_list(engine: Engine, **options: Any) -> Dict[str, Any]:
    url = Route.pornstar_list(**options)
    res = engine.request.get(url)
    soup = get_soup(res.text)
    return {"data": parse_pornstar_result(soup, "#popularPornstars"), "paging": parse_paging(soup)}


def recommended(engine: Engine, **options: Any) -> Dict[str, Any]:
    url = Route.recommended_page(**options)
    res = engine.request.get(url)
    soup = get_soup(res.text)
    return {"data": parse_video_result(soup, ".recommendedVideosContainer"), "paging": parse_paging(soup)}


def album_search(engine: Engine, keyword: str, **options: Any) -> Dict[str, Any]:
    url = Route.album_search(keyword, **options)
    res = engine.request.get(url)
    soup = get_soup(res.text)
    data = []
    for item in soup.select("ul#photosAlbumsSection li.photoAlbumListContainer div.photoAlbumListBlock"):
        title = get_attr(item, "title", "") or ""
        path = get_attr(item.find("a"), "href", "") or ""
        url_item = urljoin(BASE_URL, path)
        rating = text_or_empty(item.select_one(".album-photo-percentage"))
        preview = get_data(item, "bkg", "")
        if not preview:
            style = get_attr(item, "style", "")
            match = re.search(r'url\("(.+)"\)', style or "")
            preview = match.group(1) if match else ""
        data.append({"title": title, "url": url_item, "rating": rating, "preview": preview})
    return {"data": data, "paging": parse_paging(soup), "counting": parse_counting(soup)}


def gif_search(engine: Engine, keyword: str, **options: Any) -> Dict[str, Any]:
    url = Route.gif_search(keyword, **options)
    res = engine.request.get(url)
    soup = get_soup(res.text)
    data = []
    for item in soup.select("ul.gifLink li.gifVideoBlock"):
        video = item.find("video")
        poster = get_attr(video, "poster", "") or ""
        path = get_attr(item.find("a"), "href", "") or ""
        data.append(
            {
                "title": text_or_empty(item.select_one(".title")),
                "url": urljoin(BASE_URL, path),
                "mp4": get_data(video, "mp4", "") or "",
                "webm": get_data(video, "webm", "") or "",
                "preview": remove_protection_bracket(poster),
            }
        )
    return {"data": data, "paging": parse_paging(soup), "counting": parse_counting(soup)}


def channel_search(engine: Engine, keyword: str, **options: Any) -> Dict[str, Any]:
    url = Route.channel_search(keyword, **options)
    res = engine.request.get(url)
    soup = get_soup(res.text)
    data = []
    for item in soup.select("ul.channelGridWrapper > li > .channelsWrapper"):
        img_wrapper = item.select_one(".imgWrapper")
        description = item.select_one(".description")
        rank_text = text_or_empty(img_wrapper.select_one(".rank"))
        try:
            rank = int(rank_text.replace("Rank", "").strip())
        except Exception:
            rank = 0

        description_container = description.select_one(".descriptionContainer > ul") if description else None
        description_grid = description_container.find_all("li", recursive=False) if description_container else []
        if description_container and len(description_grid) < 4:
            continue

        photo = description.select_one(".avatar img") if description else None
        first = description_grid[0] if description_grid else None
        name = text_or_empty(first.select_one("a")) if first else ""
        url_path = get_attr(first.select_one("a"), "href", "") if first else ""
        subs_text = text_or_empty(description_grid[1].select_one("span")) if len(description_grid) > 1 else ""
        video_num_text = text_or_empty(description_grid[2].select_one("span")) if len(description_grid) > 2 else ""
        views_text = text_or_empty(description_grid[3].select_one("span")) if len(description_grid) > 3 else ""
        data.append(
            {
                "name": name,
                "url": urljoin(BASE_URL, url_path) if url_path else "",
                "subscribers": int(remove_comma(subs_text) or 0),
                "videoNum": int(remove_comma(video_num_text) or 0),
                "views": int(remove_comma(views_text) or 0),
                "rank": rank,
                "photo": get_data(photo, "thumb_url", "") if photo else "",
            }
        )
    return {"data": data, "paging": parse_paging(soup)}


def pornstar_search(engine: Engine, keyword: str, **options: Any) -> Dict[str, Any]:
    url = Route.pornstar_search(keyword, **options)
    res = engine.request.get(url)
    soup = get_soup(res.text)
    data = []
    for item in soup.select("ul#pornstarsSearchResult li div.wrap"):
        path = get_attr(item.find("a"), "href", "") or ""
        img = item.find("img")
        data.append(
            {
                "name": text_or_empty(item.select_one(".title")),
                "url": urljoin(BASE_URL, path),
                "views": text_or_empty(item.select_one(".pstarViews")).replace("views", "").strip() or "0",
                "videoNum": int(text_or_empty(item.select_one(".videosNumber")) or 0),
                "rank": int(text_or_empty(item.select_one(".rank_number")) or 0),
                "photo": get_data(img, "thumb_url", "") if img else "",
            }
        )
    return {"data": data, "paging": parse_paging(soup), "counting": parse_counting(soup)}


def model_search(engine: Engine, keyword: str, **options: Any) -> List[Dict[str, Any]]:
    result = get_auto_complete(engine, keyword, **options)
    return result.get("models", [])


def video_search(engine: Engine, keyword: str, **options: Any) -> Dict[str, Any]:
    url = Route.video_search(keyword, **options)
    res = engine.request.get(url)
    soup = get_soup(res.text)
    return {"data": parse_video_result(soup, "#videoSearchResult"), "paging": parse_paging(soup), "counting": parse_counting(soup)}
