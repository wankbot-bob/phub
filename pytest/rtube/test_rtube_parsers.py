from app.client.rtube.parsers import parse_video_list, parse_performer_profile


def test_parse_video_list_basic():
    html = """
    <div class="video-item">
      <a href="https://www.redtube.com/12345" title="Sample Video">
        <img src="thumb.jpg" />
        <span class="duration">1:23</span>
        <span class="views">1000 views</span>
      </a>
    </div>
    """
    items = parse_video_list(html)
    assert len(items) == 1
    video = items[0]
    assert video["id"] == "12345"
    assert video["title"] == "Sample Video"
    assert video["preview"] == "thumb.jpg"
    assert video["duration"] == "1:23"
    assert "1000" in video["views"]


def test_parse_performer_profile_basic():
    html = """
    <h1>Performer Name</h1>
    <img class="avatar" src="avatar.jpg" />
    <div class="bio">Bio text</div>
    """
    profile = parse_performer_profile(html)
    assert profile["name"] == "Performer Name"
    assert profile["avatar"] == "avatar.jpg"
    assert "Bio" in profile["bio"]
