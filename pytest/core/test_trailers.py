from app.core.trailers import build_trailer_map
from app.client.phub.pipelines.channel_pipeline import build_parser as build_channel_parser
from app.client.phub.pipelines.performer_pipeline import build_parser as build_performer_parser, _enrich_video_details


def test_build_trailer_map_primary_and_fallback():
    html = """
    <ul>
      <li data-video-vkey="abc">
        <div data-mediabook="http://example.com/a.webm"></div>
      </li>
    </ul>
    <div>
      <a href="/view_video.php?viewkey=def">
        <img data-mediabook="http://example.com/b.webm" />
      </a>
    </div>
    """
    from app.client.phub.utils import get_soup

    soup = get_soup(html)
    trailer_map = build_trailer_map(soup)
    assert trailer_map["abc"] == "http://example.com/a.webm"
    assert trailer_map["def"] == "http://example.com/b.webm"


def test_channel_parser_flags():
    parser = build_channel_parser()
    args = parser.parse_args(
        [
            "https://www.pornhub.com/channels/foo",
            "--enrich-details",
            "--workers",
            "2",
            "--detail-timeout",
            "3",
            "--detail-total-timeout",
            "4",
            "--verbose",
        ]
    )
    assert args.enrich_details is True
    assert args.workers == 2
    assert args.detail_timeout == 3
    assert args.detail_total_timeout == 4
    assert args.verbose is True


def test_performer_parser_flags():
    parser = build_performer_parser()
    args = parser.parse_args(
        [
            "https://www.pornhub.com/pornstar/foo",
            "--enrich-details",
            "--workers",
            "3",
            "--detail-timeout",
            "6",
            "--detail-total-timeout",
            "9",
            "--verbose",
        ]
    )
    assert args.enrich_details is True
    assert args.workers == 3
    assert args.detail_timeout == 6
    assert args.detail_total_timeout == 9
    assert args.verbose is True


def test_enrich_video_details_uses_stub():
    class StubPH:
        def video(self, url_or_id):
            return {"preview": "p", "views": 123, "duration": 9, "title": "t"}

    videos = [{"id": "1", "url": "1", "preview": "", "views": 0, "duration": 0, "title": ""}]
    enriched = _enrich_video_details(StubPH(), videos, max_workers=1, timeout=1)
    assert enriched[0]["preview"] == "p"
    assert enriched[0]["views"] == 123
    assert enriched[0]["duration"] == 9
    assert enriched[0]["title"] == "t"
