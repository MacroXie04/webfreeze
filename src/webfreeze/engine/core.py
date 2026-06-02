"""Core engine functions decoupled from the CLI.

These are pure building blocks (fetch + parse) reused by both the CLI and the
web service. They deliberately do NOT inline resources or write files — the
caller decides whether to inline to base64 (CLI/export) or rewrite to a proxy
(preview).
"""

from dataclasses import dataclass
from typing import Optional, Tuple

from bs4 import BeautifulSoup

from ..cache import ResourceCache
from ..detector import should_render
from ..fetchers.rendered import RenderedFetcher
from ..fetchers.static import StaticFetcher
from ..utils import get_effective_base_url, log_info


@dataclass
class FetchOpts:
    """Options controlling how a page is fetched/rendered."""

    inline_images: bool = False
    wait_for: Optional[str] = None
    wait_timeout: int = 30000
    scroll: bool = True
    script_policy: str = "strip_all"


def render_or_fetch(
    url: str, mode: str, opts: FetchOpts, cache: ResourceCache
) -> Tuple[BeautifulSoup, str]:
    """Fetch (and optionally render) a URL, returning ``(soup, base_url)``.

    Mirrors the fetch/detect logic previously inline in ``cli.process_single``:
    in ``"auto"`` mode a cheap static fetch decides whether to switch to render.
    Resources are not inlined and nothing is written to disk.
    """
    static_fetcher = StaticFetcher(cache.session)

    final_html = ""
    fetch_mode = mode

    if mode == "auto":
        raw_html = static_fetcher.fetch(url)
        if should_render(raw_html):
            log_info("SPA/Dynamic content detected. Switching to RENDER mode.")
            fetch_mode = "render"
        else:
            log_info("Static content detected. Using STATIC mode.")
            fetch_mode = "static"
            final_html = raw_html

    if fetch_mode == "static":
        if not final_html:
            final_html = static_fetcher.fetch(url)
    else:
        rendered_fetcher = RenderedFetcher(
            wait_for=opts.wait_for,
            timeout=opts.wait_timeout,
            scroll=opts.scroll,
            script_policy=opts.script_policy,
        )
        final_html = rendered_fetcher.fetch(url)

    soup = BeautifulSoup(final_html, "html.parser")
    base_url = get_effective_base_url(soup, url)
    return soup, base_url
