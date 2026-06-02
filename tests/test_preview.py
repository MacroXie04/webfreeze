from unittest.mock import MagicMock

from bs4 import BeautifulSoup

from webfreeze.server.preview import rewrite_for_preview, unrewrite_proxy_urls


def _soup(html):
    return BeautifulSoup(html, "html.parser")


def test_rewrite_img_src_to_proxy():
    soup = _soup("<html><body><img src='/logo.png'></body></html>")
    rewrite_for_preview(soup, "https://example.com/", "SID", MagicMock())
    src = soup.find("img")["src"]
    assert src.startswith("/proxy?url=")
    assert "logo.png" in src
    assert "sid=SID" in src


def test_rewrite_skips_data_uri():
    soup = _soup("<html><body><img src='data:image/png;base64,AAAA'></body></html>")
    rewrite_for_preview(soup, "https://example.com/", "SID", MagicMock())
    assert soup.find("img")["src"] == "data:image/png;base64,AAAA"


def test_rewrite_style_url():
    soup = _soup(
        "<html><head><style>body{background:url('bg.png')}</style></head><body></body></html>"
    )
    rewrite_for_preview(soup, "https://example.com/", "SID", MagicMock())
    css = soup.find("style").string
    assert "/proxy?url=" in css
    assert "bg.png" in css


def test_rewrite_srcset():
    soup = _soup("<html><body><img srcset='a.png 1x, b.png 2x'></body></html>")
    rewrite_for_preview(soup, "https://example.com/", "SID", MagicMock())
    srcset = soup.find("img")["srcset"]
    assert srcset.count("/proxy?url=") == 2
    assert "1x" in srcset and "2x" in srcset


def test_injects_bootstrap():
    soup = _soup("<html><body><p>x</p></body></html>")
    rewrite_for_preview(soup, "https://example.com/", "SID", MagicMock())
    assert soup.find("script", attrs={"data-wf-ui": "bootstrap"}) is not None


def test_unrewrite_roundtrip():
    soup = _soup(
        "<html><body><img src='/logo.png'>"
        "<script data-wf-ui='bootstrap'>x</script></body></html>"
    )
    rewrite_for_preview(soup, "https://example.com/", "SID", MagicMock())
    unrewrite_proxy_urls(soup)
    assert soup.find("img")["src"] == "https://example.com/logo.png"
    assert soup.find(attrs={"data-wf-ui": "bootstrap"}) is None
