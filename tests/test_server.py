from unittest.mock import MagicMock

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from webfreeze.cache import ResourceCache
from webfreeze.server import app as app_module
from webfreeze.server.app import create_app
from webfreeze.server.session import Session, SessionStore


def _client_with_session(monkeypatch, page):
    """A TestClient with render_or_fetch mocked to return `page` (no network)."""
    monkeypatch.setattr(
        app_module,
        "render_or_fetch",
        lambda url, mode, opts, cache: (BeautifulSoup(page, "html.parser"), "https://example.com/"),
    )
    client = TestClient(create_app())
    resp = client.post("/api/session", json={"url": "https://example.com/"})
    assert resp.status_code == 200
    return client, resp.json()


def _store_with_session(cache):
    store = SessionStore()
    sid = store.new_id()
    soup = BeautifulSoup("<html></html>", "html.parser")
    store.save(
        sid,
        Session(
            soup=soup,
            soup_preview=soup,
            base_url="https://example.com/",
            origin="https://example.com",
            cache=cache,
            title="t",
        ),
    )
    return store, sid


def test_health():
    client = TestClient(create_app())
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_create_session_returns_preview_url(monkeypatch):
    page = "<html><head><title>My Page</title></head><body><img src='/logo.png'></body></html>"
    client, data = _client_with_session(monkeypatch, page)
    assert data["sessionId"]
    assert data["previewUrl"] == f"/api/session/{data['sessionId']}/preview"
    assert data["title"] == "My Page"


def test_preview_returns_rewritten_html(monkeypatch):
    page = "<html><head><title>T</title></head><body><img src='/logo.png'></body></html>"
    client, data = _client_with_session(monkeypatch, page)
    resp = client.get(data["previewUrl"])
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "/proxy?url=" in resp.text
    assert "logo.png" in resp.text


def test_preview_unknown_session_404():
    client = TestClient(create_app())
    assert client.get("/api/session/nope/preview").status_code == 404


def test_proxy_streams_bytes():
    cache = MagicMock(spec=ResourceCache)
    cache.fetch.return_value = ("image/png", b"PNGDATA")
    store, sid = _store_with_session(cache)
    client = TestClient(create_app(store=store))
    resp = client.get("/proxy", params={"url": "https://example.com/x.png", "sid": sid})
    assert resp.status_code == 200
    assert resp.content == b"PNGDATA"
    assert resp.headers["content-type"].startswith("image/png")


def test_proxy_css_is_rewritten():
    cache = MagicMock(spec=ResourceCache)
    cache.fetch.return_value = ("text/css", b"a{background:url('/img.png')}")
    store, sid = _store_with_session(cache)
    client = TestClient(create_app(store=store))
    resp = client.get("/proxy", params={"url": "https://example.com/s.css", "sid": sid})
    assert resp.status_code == 200
    assert "/proxy?url=" in resp.text
    assert "img.png" in resp.text


def test_proxy_unknown_session_404():
    client = TestClient(create_app())
    resp = client.get("/proxy", params={"url": "https://example.com/x", "sid": "nope"})
    assert resp.status_code == 404


def test_proxy_rejects_non_http_scheme():
    cache = MagicMock(spec=ResourceCache)
    store, sid = _store_with_session(cache)
    client = TestClient(create_app(store=store))
    resp = client.get("/proxy", params={"url": "file:///etc/passwd", "sid": sid})
    assert resp.status_code == 400


def test_freeze_whole_page_inlines_and_strips_js(monkeypatch):
    page = (
        "<html><head><title>T</title></head><body>"
        "<h1>Hello</h1><script>alert(1)</script></body></html>"
    )
    client, data = _client_with_session(monkeypatch, page)
    resp = client.post("/api/freeze", json={"sessionId": data["sessionId"], "keep": "whole"})
    assert resp.status_code == 200
    body = resp.json()
    assert "<h1>Hello</h1>" in body["html"]
    assert body["html"].lstrip().lower().startswith("<!doctype")
    assert "alert(1)" not in body["html"]  # jsFidelity="off" strips scripts
    assert body["report"]["keptScripts"] == 0


def test_freeze_unknown_session_404():
    client = TestClient(create_app())
    resp = client.post("/api/freeze", json={"sessionId": "nope", "keep": "whole"})
    assert resp.status_code == 404
