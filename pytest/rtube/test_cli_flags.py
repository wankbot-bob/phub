from app.client.rtube.pipelines.performer_pipeline import main as performer_main
from app.client.rtube.pipelines.channel_pipeline import main as channel_main
from app.client.rtube.pipelines.video_pipeline import main as video_main


def test_performer_flag_shortcut(monkeypatch, capsys):
    monkeypatch.setattr("app.client.rtube.pipelines.performer_pipeline.collect_performer", lambda *a, **k: {"ok": True})
    performer_main(["--performer", "foo"])
    out = capsys.readouterr().out
    assert '"ok": true' in out


def test_channel_flag_shortcut(monkeypatch, capsys):
    monkeypatch.setattr("app.client.rtube.pipelines.channel_pipeline.collect_channel", lambda *a, **k: {"ok": True})
    channel_main(["--channel", "bar"])
    out = capsys.readouterr().out
    assert '"ok": true' in out


def test_video_flag_shortcut(monkeypatch, capsys):
    monkeypatch.setattr("app.client.rtube.pipelines.video_pipeline.fetch_with_yt_dlp", lambda url: {"url": url})
    video_main(["--id", "123"])
    out = capsys.readouterr().out
    assert "123" in out
