import re

from app.core.utils import slugify


class UrlParser:
    video_re = re.compile(r"redtube\.com/(\d+)")
    channel_re = re.compile(r"redtube\.com/channels/([\w-]+)")
    performer_re = re.compile(r"redtube\.com/pornstar/([\w-]+)")

    @classmethod
    def get_video_id(cls, value: str) -> str:
        match = cls.video_re.search(value)
        return match.group(1) if match else value.rstrip("/").split("/")[-1]

    @classmethod
    def get_channel_slug(cls, value: str) -> str:
        match = cls.channel_re.search(value)
        return match.group(1) if match else slugify(value)

    @classmethod
    def get_performer_slug(cls, value: str) -> str:
        match = cls.performer_re.search(value)
        return match.group(1) if match else slugify(value)
