from unittest.mock import MagicMock
from bs4 import BeautifulSoup
from webfreeze.inliner import Inliner
from webfreeze.cache import ResourceCache

def test_inline_css_url():
    cache = MagicMock(spec=ResourceCache)
    inliner = Inliner(cache, inline_images=False)
    
    css_text = "body { background: url('bg.png'); }"
    # Should resolve to absolute if inline_images=False
    resolved = inliner.inline_css(css_text, "https://example.com/")
    assert "url(\"https://example.com/bg.png\")" in resolved

def test_inline_css_url_base64():
    cache = MagicMock(spec=ResourceCache)
    cache.fetch_base64.return_value = "data:image/png;base64,mocked"
    inliner = Inliner(cache, inline_images=True)
    
    css_text = "body { background: url('bg.png'); }"
    resolved = inliner.inline_css(css_text, "https://example.com/")
    assert "url(\"data:image/png;base64,mocked\")" in resolved

def test_process_soup_link_to_style():
    cache = MagicMock(spec=ResourceCache)
    cache.fetch.return_value = ("text/css", b"p { color: red; }")
    inliner = Inliner(cache)
    
    html = """
    <html>
        <head>
            <link rel="stylesheet" href="style.css">
        </head>
        <body></body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    inliner.process_soup(soup, "https://example.com/")
    
    assert soup.find("style") is not None
    assert "p { color: red; }" in soup.find("style").string
    assert soup.find("link") is None
