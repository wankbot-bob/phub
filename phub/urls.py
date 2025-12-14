import re

from .utils import slugify


class UrlParser:
    video_re = re.compile(r"[\w]+\.pornhub\.com/view_video\.php\?viewkey=([a-zA-Z0-9]{1,30})")
    album_re = re.compile(r"[\w]+\.pornhub\.com/album/([0-9]{1,30})")
    photo_re = re.compile(r"[\w]+\.pornhub\.com/photo/([0-9]{1,30})")
    pornstar_re = re.compile(r"[\w]+\.pornhub\.com/pornstar/([a-zA-Z0-9-]{1,30})")
    model_re = re.compile(r"[\w]+\.pornhub\.com/model/([a-zA-Z0-9-]{1,30})")
    channel_re = re.compile(r"[\w]+\.pornhub\.com/channels/([a-zA-Z0-9-]{1,30})")

    @classmethod
    def get_video_id(cls, value: str) -> str:
        match = cls.video_re.search(value)
        return match.group(1) if match else value

    @classmethod
    def get_album_id(cls, value: str) -> str:
        match = cls.album_re.search(value)
        return match.group(1) if match else value

    @classmethod
    def get_photo_id(cls, value: str) -> str:
        match = cls.photo_re.search(value)
        return match.group(1) if match else value

    @classmethod
    def get_pornstar_name(cls, value: str) -> str:
        match = cls.pornstar_re.search(value)
        return match.group(1) if match else slugify(value)

    @classmethod
    def get_model_name(cls, value: str) -> str:
        match = cls.model_re.search(value)
        return match.group(1) if match else slugify(value)

    @classmethod
    def get_channel_name(cls, value: str) -> str:
        match = cls.channel_re.search(value)
        return match.group(1) if match else slugify(value)
