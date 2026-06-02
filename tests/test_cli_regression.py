"""Byte-identity guard for the P0 engine decoupling.

``fixtures/golden_static.html`` was generated from the pre-refactor code path.
This test runs the refactored ``process_single`` against the same deterministic,
network-free input and asserts the written bytes are unchanged.
"""

from pathlib import Path

from webfreeze import cli
from webfreeze.fetchers.static import StaticFetcher

from ._golden_fixture import PAGE_URL, SOURCE_HTML, make_cache

FIXTURES = Path(__file__).parent / "fixtures"


def test_process_single_byte_identical(tmp_path, monkeypatch):
    monkeypatch.setattr(StaticFetcher, "fetch", lambda self, url: SOURCE_HTML)

    out = tmp_path / "out.html"
    cli.process_single(
        PAGE_URL,
        str(out),
        "static",
        True,   # inline_images
        None,   # wait_for
        30000,  # wait_timeout
        True,   # scroll
        False,  # keep_js
        make_cache(),
    )

    produced = out.read_bytes()
    golden = (FIXTURES / "golden_static.html").read_bytes()
    assert produced == golden
