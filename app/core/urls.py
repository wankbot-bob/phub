import re

from app.core.utils import slugify


class UrlParser:
    video_re = re.compile(r"view_video\.php\?viewkey=([a-zA-Z0-9]+)")
    album_re = re.compile(r"/album/([0-9]{1,30})")
    photo_re = re.compile(r"/photo/([0-9]{1,30})")
    pornstar_re = re.compile(r"/pornstar/([a-zA-Z0-9-]{1,30})")
    model_re = re.compile(r"/model/([a-zA-Z0-9-]{1,30})")
    channel_re = re.compile(r"/channels/([a-zA-Z0-9-]{1,30})")

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
