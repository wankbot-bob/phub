from urllib.parse import parse_qs, urlparse

from phub.routes import Route


def test_video_search_route_builds_expected_params():
    url = Route.video_search(
        "tokyo hot",
        page=2,
        order="Most Viewed",
        hd=True,
        production="homemade",
        duration_min=10,
        duration_max=30,
        filter_category=5,
        sexual_orientation="gay",
        period="weekly",
    )
    parsed = urlparse(url)
    assert parsed.path.startswith("/gay/video/search")
    qs = parse_qs(parsed.query)
    assert qs["search"] == ["tokyo+hot"]
    assert qs["page"] == ["2"]
    assert qs["o"] == ["mv"]
    assert qs["hd"] == ["1"]
    assert qs["p"] == ["homemade"]
    assert qs["min_duration"] == ["10"]
    assert qs["max_duration"] == ["30"]
    assert qs["filter_category"] == ["5"]
    assert qs["t"] == ["w"]


def test_pornstar_list_route_respects_order_and_letter():
    url = Route.pornstar_list(order="Alphabetical", letter="C")
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    assert qs["o"] == ["a"]
    assert qs["letter"] == ["c"]


def test_recommended_route_defaults_to_straight_segment():
    url = Route.recommended_page()
    parsed = urlparse(url)
    assert parsed.path == "/recommended"
