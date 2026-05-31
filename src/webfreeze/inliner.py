import re
from typing import Optional

from bs4 import BeautifulSoup

from .cache import ResourceCache
from .utils import is_data_uri, log_warn, resolve_url

class Inliner:
    """Core logic for inlining CSS and images into HTML."""

    def __init__(self, cache: ResourceCache, inline_images: bool = False):
        self.cache = cache
        self.inline_images = inline_images

    def inline_css(self, css_text: str, base_url: str) -> str:
        """Recursively resolve @import and inline url() references in CSS."""

        # Handle @import url(...) or @import "..."
        def import_repl(m: re.Match) -> str:
            imp = m.group(1).strip("'\"")
            full = resolve_url(base_url, imp)
            try:
                _, content = self.cache.fetch(full)
                # Recurse for nested imports
                return self.inline_css(
                    content.decode("utf-8", errors="replace"), full
                )
            except Exception as e:
                log_warn(f"@import failed: {full} ({e})")
                return ""

        css_text = re.sub(
            r'@import\s+(?:url\()?["\']?([^"\')]+)["\']?\)?\s*;',
            import_repl,
            css_text,
        )

        # Handle url(...) — fonts, background images, etc.
        def url_repl(m: re.Match) -> str:
            raw = m.group(1).strip("'\"")
            if is_data_uri(raw) or raw.startswith("#"):
                return m.group(0)
            
            full = resolve_url(base_url, raw)
            if self.inline_images:
                try:
                    return f'url("{self.cache.fetch_base64(full)}")'
                except Exception as e:
                    log_warn(f"Resource failed: {full} ({e})")
                    return f'url("{full}")'
            
            return f'url("{full}")'

        return re.sub(r"url\(([^)]+)\)", url_repl, css_text)

    def process_soup(self, soup: BeautifulSoup, url: str) -> None:
        """Process the BeautifulSoup object to inline resources."""
        base_tag = soup.find("base", href=True)
        base_url = resolve_url(url, base_tag["href"]) if base_tag else url

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
                    img.attrs.pop("loading", None) # Remove lazy loading
                except Exception as e:
                    log_warn(f"Failed to inline image {img_url}: {e}")
                    img["src"] = img_url
