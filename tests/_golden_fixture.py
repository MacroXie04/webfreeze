"""Shared fixture for the CLI byte-identity regression test (P0).

This module is intentionally NOT named ``test_*`` so pytest does not collect it
as a test module. It provides a deterministic, network-free input page plus a
mocked ``ResourceCache`` so ``process_single`` produces byte-stable output. The
golden file ``fixtures/golden_static.html`` is generated once from the
pre-refactor code path; ``test_cli_regression.py`` then asserts the refactored
``process_single`` reproduces it exactly.
"""

from unittest.mock import MagicMock

from webfreeze.cache import ResourceCache

# The page that StaticFetcher.fetch is monkeypatched to return. Exercises the
# byte-sensitive surfaces: inline <style> with a relative url(), a linked
# stylesheet (-> <style>), an <img>, an unescaped ``&`` inside <script>, and a
# pre-existing DOCTYPE.
SOURCE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Golden &amp; Static</title>
<link rel="stylesheet" href="/style.css">
<style>body { background: url('bg.png'); color: #123; }</style>
</head>
<body>
<h1>Hello &amp; Welcome</h1>
<img src="/logo.png" alt="logo">
<p>Some content that is long enough to be a real paragraph of text.</p>
<script>var x = 1 & 2; if (x < 3 && x > 0) { console.log(x); }</script>
</body>
</html>
"""

PAGE_URL = "https://example.com/"

# Absolute URL -> (Content-Type, raw bytes) for everything ResourceCache fetches.
RESOURCES = {
    "https://example.com/style.css": ("text/css", b"p { color: red; }\n"),
    "https://example.com/bg.png": ("image/png", b"\x89PNG\r\n\x1a\nBGDATA-deterministic"),
    "https://example.com/logo.png": ("image/png", b"\x89PNG\r\n\x1a\nLOGODATA-deterministic"),
}


def make_cache() -> ResourceCache:
    """A ResourceCache whose session serves RESOURCES with no real network."""
    session = MagicMock()

    def fake_get(url, timeout=None):
        resp = MagicMock()
        content_type, content = RESOURCES[url]
        resp.headers = {"Content-Type": content_type}
        resp.content = content
        resp.raise_for_status = lambda: None
        return resp

    session.get.side_effect = fake_get
    return ResourceCache(session=session)
