from phub.urls import UrlParser


def test_url_parser_extracts_ids_and_names():
    assert UrlParser.get_video_id("https://www.pornhub.com/view_video.php?viewkey=ph123") == "ph123"
    assert UrlParser.get_video_id("ph999") == "ph999"
    assert UrlParser.get_album_id("https://www.pornhub.com/album/12345") == "12345"
    assert UrlParser.get_photo_id("https://www.pornhub.com/photo/98765") == "98765"
    assert UrlParser.get_pornstar_name("https://www.pornhub.com/pornstar/eva-elfie") == "eva-elfie"
    assert UrlParser.get_model_name("Luna Okko") == "Luna-Okko"
    assert UrlParser.get_channel_name("https://www.pornhub.com/channels/brazzers") == "brazzers"
