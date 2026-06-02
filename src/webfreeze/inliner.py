import re
from typing import Callable, Optional

from bs4 import BeautifulSoup

from .cache import ResourceCache
from .utils import get_effective_base_url, is_data_uri, log_warn, resolve_url

# Match @import "url" / @import url(...) and a url(...) reference. Promoted to
# module constants so the preview proxy path (server/preview.py) reuses the
# exact same matching as the base64 inliner.
IMPORT_RE = re.compile(r'@import\s+(?:url\()?["\']?([^"\')]+)["\']?\)?\s*;')
URL_RE = re.compile(r"url\(([^)]+)\)")

class Inliner:
    """Core logic for inlining CSS and images into HTML."""

    def __init__(self, cache: ResourceCache, inline_images: bool = False):
        self.cache = cache
        self.inline_images = inline_images

    def inline_css(
        self,
        css_text: str,
        base_url: str,
        url_target: Optional[Callable[[str], str]] = None,
    ) -> str:
        """Resolve @import and url() references in CSS.

        Default (``url_target=None``): @import is fetched and inlined recursively,
        and url() is either base64-inlined (when ``inline_images``) or resolved to
        an absolute URL. When ``url_target`` is provided, both @import and url()
        targets are rewritten via ``url_target(absolute_url)`` instead (used to
        point resources at the /proxy endpoint for the live preview); nothing is
        fetched in that mode.
        """

        # Handle @import url(...) or @import "..."
        def import_repl(m: re.Match) -> str:
            imp = m.group(1).strip("'\"")
            full = resolve_url(base_url, imp)
            if url_target is not None:
                return f'@import url("{url_target(full)}");'
            try:
                _, content = self.cache.fetch(full)
                # Recurse for nested imports
                return self.inline_css(
                    content.decode("utf-8", errors="replace"), full
                )
            except Exception as e:
                log_warn(f"@import failed: {full} ({e})")
                return ""

        css_text = IMPORT_RE.sub(import_repl, css_text)

        # Handle url(...) — fonts, background images, etc.
        def url_repl(m: re.Match) -> str:
            raw = m.group(1).strip("'\"")
            if is_data_uri(raw) or raw.startswith("#"):
                return m.group(0)

            full = resolve_url(base_url, raw)
            if url_target is not None:
                return f'url("{url_target(full)}")'
            if self.inline_images:
                try:
                    return f'url("{self.cache.fetch_base64(full)}")'
                except Exception as e:
                    log_warn(f"Resource failed: {full} ({e})")
                    return f'url("{full}")'

            return f'url("{full}")'

        return URL_RE.sub(url_repl, css_text)

    def process_soup(self, soup: BeautifulSoup, url: str) -> None:
        """Process the BeautifulSoup object to inline resources."""
        base_url = get_effective_base_url(soup, url)

        # 1) Inline existing <style> tags
        for style in soup.find_all("style"):
            if style.string:
                style.string = self.inline_css(style.string, base_url)

        # 2) Convert <link rel="stylesheet"> to <style>
        links = soup.find_all("link", rel=lambda v: v and "stylesheet" in v.lower())
        for link in links:
            href = link.get("href")
            if not href:
                continue
            css_url = resolve_url(base_url, href)
            try:
                _, content = self.cache.fetch(css_url)
                css_text = self.inline_css(
                    content.decode("utf-8", errors="replace"), css_url
                )
                new_style = soup.new_tag("style")
                new_style.string = css_text
                link.replace_with(new_style)
            except Exception as e:
                log_warn(f"Failed to inline stylesheet {css_url}: {e}")

        # 3) Inline images in <img> tags
        if self.inline_images:
            for img in soup.find_all("img"):
                # Prefer data-src or other common lazy-load attributes if src is empty/placeholder
                src = img.get("src")
                for attr in ["data-src", "data-original", "lazy-src"]:
                    if not src or "data:image" in src or len(src) < 10:
                        if img.get(attr):
                            src = img.get(attr)
                            break

                if not src or is_data_uri(src):
                    continue

                img_url = resolve_url(base_url, src)
                try:
                    img["src"] = self.cache.fetch_base64(img_url)
                    # Remove srcset to ensure the inlined src is used
                    img.attrs.pop("srcset", None)
                    img.attrs.pop("loading", None)  # Remove lazy loading
                except Exception as e:
                    log_warn(f"Failed to inline image {img_url}: {e}")
                    img["src"] = img_url
