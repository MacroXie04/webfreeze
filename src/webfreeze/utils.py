import logging
import sys
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

# Module logger. A NullHandler keeps the CLI's stderr output byte-identical (no
# "lastResort" emission to stderr); the web server attaches its own handler to
# the "webfreeze" logger to capture engine logs.
logger = logging.getLogger("webfreeze")
logger.addHandler(logging.NullHandler())

def resolve_url(base_url: str, url: str) -> str:
    """Resolve a relative URL against a base URL."""
    if not url:
        return ""
    # Already absolute or data URI
    if urlparse(url).scheme or url.startswith("data:"):
        return url
    return urljoin(base_url, url)

def is_data_uri(url: str) -> bool:
    """Check if a URL is a data URI."""
    return url.startswith("data:")

def get_effective_base_url(soup: BeautifulSoup, url: str) -> str:
    """Return the base URL for resolving resources, honoring any <base href>."""
    base_tag = soup.find("base", href=True)
    return resolve_url(url, base_tag["href"]) if base_tag else url

def dumps_html(soup: BeautifulSoup) -> str:
    """Serialize a BeautifulSoup document to an HTML string.

    Uses formatter=None so BeautifulSoup does not escape characters inside
    <script> and <style> (e.g. & -> &amp;), which can break CSS/JS logic, and
    ensures a DOCTYPE is present.
    """
    html_content = soup.encode(formatter=None).decode("utf-8")

    # Ensure DOCTYPE is present
    if not html_content.lstrip().lower().startswith("<!doctype"):
        html_content = "<!DOCTYPE html>\n" + html_content

    return html_content

def save_html(soup: BeautifulSoup, file_path: str) -> None:
    """Save a BeautifulSoup document to a file, preserving script/style contents."""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(dumps_html(soup))

def log_info(msg: str) -> None:
    logger.info(msg)
    print(f"[*] {msg}", file=sys.stderr)

def log_success(msg: str) -> None:
    logger.info(msg)
    print(f"[✓] {msg}", file=sys.stderr)

def log_error(msg: str) -> None:
    logger.error(msg)
    print(f"[✗] {msg}", file=sys.stderr)

def log_warn(msg: str) -> None:
    logger.warning(msg)
    print(f"[!] {msg}", file=sys.stderr)
