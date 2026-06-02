from unittest.mock import MagicMock

from webfreeze.engine import FetchOpts, render_or_fetch
from webfreeze.fetchers.rendered import RenderedFetcher
from webfreeze.fetchers.static import StaticFetcher


def test_render_or_fetch_static_mode(monkeypatch):
    html = "<html><head><title>T</title></head><body><p>hi</p></body></html>"
    monkeypatch.setattr(StaticFetcher, "fetch", lambda self, url: html)

    soup, base_url = render_or_fetch(
        "https://example.com/page", "static", FetchOpts(), MagicMock()
    )

    assert soup.find("title").string == "T"
    assert soup.find("p").get_text() == "hi"
    assert base_url == "https://example.com/page"


def test_render_or_fetch_auto_uses_static_for_rich_page(monkeypatch):
    html = "<html><body>" + "<p>Lots of real content here.</p>" * 20 + "</body></html>"
    monkeypatch.setattr(StaticFetcher, "fetch", lambda self, url: html)

    def boom(self, url):  # pragma: no cover - must never run
        raise AssertionError("RenderedFetcher must not be called for static content")

    monkeypatch.setattr(RenderedFetcher, "fetch", boom)

    soup, _ = render_or_fetch("https://example.com/", "auto", FetchOpts(), MagicMock())
    assert soup.find("p") is not None


def test_render_or_fetch_honors_base_tag(monkeypatch):
    html = (
        '<html><head><base href="https://cdn.example.com/assets/"></head>'
        "<body>x</body></html>"
    )
    monkeypatch.setattr(StaticFetcher, "fetch", lambda self, url: html)

    _, base_url = render_or_fetch(
        "https://example.com/page", "static", FetchOpts(), MagicMock()
    )
    assert base_url == "https://cdn.example.com/assets/"
