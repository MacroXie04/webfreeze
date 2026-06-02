"""HP1 — rewrite a rendered page so the preview iframe loads every resource
through the backend /proxy endpoint (bypassing CORS), and inject the picker
bootstrap. The reverse (`unrewrite_proxy_urls`) turns a grabbed preview DOM back
into original absolute URLs before the final inline/export.
"""

from typing import Callable
from urllib.parse import parse_qs, quote, urlsplit

from bs4 import BeautifulSoup

from ..inliner import Inliner
from ..utils import get_effective_base_url, is_data_uri, resolve_url

# Attributes carrying a single resource URL we route through /proxy.
_URL_ATTRS = (("img", "src"), ("script", "src"), ("source", "src"), ("link", "href"))

_SKIP_PREFIXES = ("#", "data:", "javascript:", "mailto:", "tel:", "blob:")

# Minimal picker bootstrap stub for P1 (full implementation lands in P2). It only
# signals readiness; it carries data-wf-ui so it is stripped before export.
PICKER_BOOTSTRAP = (
    "(function(){try{parent.postMessage({type:'wf-ready'},'*');}catch(e){}})();"
)


def proxy_url(absolute_url: str, sid: str) -> str:
    return f"/proxy?url={quote(absolute_url, safe='')}&sid={sid}"


def _should_skip(value: str) -> bool:
    return not value or value.startswith(_SKIP_PREFIXES)


def _rewrite_srcset(srcset: str, base_url: str, to_proxy: Callable[[str], str]) -> str:
    out = []
    for entry in srcset.split(","):
        entry = entry.strip()
        if not entry:
            continue
        bits = entry.split(None, 1)
        url = bits[0]
        descriptor = bits[1] if len(bits) > 1 else ""
        new_url = url if _should_skip(url) else to_proxy(resolve_url(base_url, url))
        out.append((new_url + " " + descriptor).strip())
    return ", ".join(out)


def rewrite_for_preview(
    soup: BeautifulSoup, base_url: str, sid: str, cache
) -> BeautifulSoup:
    """Rewrite resource URLs to /proxy and inject the picker bootstrap (in place)."""
    base_url = get_effective_base_url(soup, base_url)

    def to_proxy(abs_url: str) -> str:
        return proxy_url(abs_url, sid)

    # 1) Single-URL attributes (img/script/source src, link href).
    for tag_name, attr in _URL_ATTRS:
        for tag in soup.find_all(tag_name):
            value = tag.get(attr)
            if value and not _should_skip(value):
                tag[attr] = to_proxy(resolve_url(base_url, value))

    # 2) srcset (img, source).
    for tag in soup.find_all(["img", "source"]):
        if tag.get("srcset"):
            tag["srcset"] = _rewrite_srcset(tag["srcset"], base_url, to_proxy)

    # 3) CSS url()/@import inside <style> -> /proxy (reuse the Inliner regex).
    inliner = Inliner(cache)
    for style in soup.find_all("style"):
        if style.string:
            style.string = inliner.inline_css(style.string, base_url, url_target=to_proxy)

    # 4) Inject the picker bootstrap as the last <body> child.
    bootstrap = soup.new_tag("script")
    bootstrap["data-wf-ui"] = "bootstrap"
    bootstrap.string = PICKER_BOOTSTRAP
    target = soup.body or soup.html or soup
    target.append(bootstrap)

    return soup


def _deproxy(value: str) -> str:
    """If value is a /proxy?url=...&sid=... link, return the original URL."""
    if not value:
        return value
    split = urlsplit(value)
    if split.path.endswith("/proxy"):
        urls = parse_qs(split.query).get("url")
        if urls:
            return urls[0]
    return value


def unrewrite_proxy_urls(soup: BeautifulSoup) -> BeautifulSoup:
    """Reverse rewrite_for_preview on a grabbed preview DOM (in place).

    Restores original absolute URLs on resource attributes and removes picker UI
    nodes so the standard Inliner can fetch + inline them for export.
    """
    for tag_name, attr in _URL_ATTRS:
        for tag in soup.find_all(tag_name):
            if tag.get(attr):
                tag[attr] = _deproxy(tag[attr])

    for tag in soup.find_all(["img", "source"]):
        if tag.get("srcset"):
            tag["srcset"] = ", ".join(
                _deproxy(part.strip().split(None, 1)[0])
                + ((" " + part.strip().split(None, 1)[1]) if len(part.strip().split(None, 1)) > 1 else "")
                for part in tag["srcset"].split(",")
                if part.strip()
            )

    for ui in soup.select("[data-wf-ui]"):
        ui.decompose()

    return soup
