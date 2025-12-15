from app.client.phub.downloader import choose_media_url


MEDIA_DEFS = [
    {"defaultQuality": False, "videoUrl": "http://example/240.m3u8", "quality": 240},
    {"defaultQuality": True, "videoUrl": "http://example/720.m3u8", "quality": [480, 720]},
    {"defaultQuality": False, "videoUrl": "http://example/1080.m3u8", "quality": 1080},
]


def test_choose_media_url_prefers_requested_quality():
    url, q = choose_media_url(MEDIA_DEFS, quality=480)
    assert q == 480
    assert url.endswith("720.m3u8")  # same media definition contains 480/720


def test_choose_media_url_prefers_default_when_no_quality_requested():
    url, q = choose_media_url(MEDIA_DEFS)
    assert q == 720
    assert url.endswith("720.m3u8")


def test_choose_media_url_falls_back_to_highest_quality():
    url, q = choose_media_url([{"defaultQuality": False, "videoUrl": "http://example/1080.m3u8", "quality": 1080}])
    assert q == 1080
    assert url.endswith("1080.m3u8")
