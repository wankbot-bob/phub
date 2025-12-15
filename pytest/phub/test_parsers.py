from bs4 import BeautifulSoup

from app.client.phub.parsers import (
    parse_counting,
    parse_media_definitions,
    parse_paging,
    parse_video_result,
)
from app.client.phub.utils import get_soup


def test_parse_media_definitions_extracts_entries():
    html = r'''
    {"defaultQuality":true,"format":"hls","videoUrl":"https:\/\/cv.phncdn.com\/videos\/202309\/01\/123\/hls.m3u8","quality":720}
    {"defaultQuality":false,"format":"hls","videoUrl":"https:\/\/cv.phncdn.com\/videos\/202309\/01\/123\/hls.m3u8","quality":[1080,720],"remote":true}
    '''
    results = parse_media_definitions(html)
    assert len(results) == 2
    assert results[0]["defaultQuality"] is True
    assert results[0]["format"] == "hls"
    assert results[0]["quality"] == 720
    assert results[1]["quality"] == [1080, 720]
    assert results[1]["remote"] is True


def test_parse_paging_and_counting():
    html = """
    <ul class="pagination3">
      <li class="page_current">2</li>
      <li class="page_next"><a>Next</a></li>
    </ul>
    <div class="showingCounter">Showing 11-20 of 42</div>
    """
    soup = get_soup(html)
    paging = parse_paging(soup)
    counting = parse_counting(soup)
    assert paging == {"current": 2, "maxPage": 2, "isEnd": False}
    assert counting == {"from": 11, "to": 20, "total": 42}


def test_parse_video_result_extracts_basic_fields():
    html = """
    <ul id="videoSearchResult">
      <li class="videoblock">
        <a class="linkVideoThumb" href="/view_video.php?viewkey=ph123" title="Sample Video"></a>
        <img src="https://img.test/preview.jpg" />
        <div class="views"><var>1,234</var></div>
        <div class="duration">10:00</div>
        <div class="marker-overlays"><span class="phpFreeBlock"></span></div>
      </li>
    </ul>
    """
    soup = BeautifulSoup(html, "lxml")
    results = parse_video_result(soup, "#videoSearchResult")
    assert len(results) == 1
    video = results[0]
    assert video["id"] == "ph123"
    assert video["title"] == "Sample Video"
    assert video["freePremium"] is True
