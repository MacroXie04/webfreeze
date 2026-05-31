import base64
import threading
from typing import Dict, Optional, Tuple

import requests

class ResourceCache:
    """A thread-safe cache for downloaded resources."""

    def __init__(self, session: Optional[requests.Session] = None):
        self._cache: Dict[str, Tuple[str, bytes]] = {}  # url -> (mime, content)
        self._lock = threading.Lock()
        self.session = session or requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            )
        })

    def fetch(self, url: str) -> Tuple[str, bytes]:
        """Fetch a resource and cache it."""
        with self._lock:
            if url in self._cache:
                return self._cache[url]

        try:
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
            
            mime = response.headers.get(
                "Content-Type", "application/octet-stream"
            ).split(";")[0]
            content = response.content
            
            with self._lock:
                self._cache[url] = (mime, content)
            
            return mime, content
        except Exception as e:
            # Re-raise to let caller handle it
            raise RuntimeError(f"Failed to fetch {url}: {e}") from e

    def fetch_base64(self, url: str) -> str:
        """Fetch a resource and return it as a data URI."""
        mime, content = self.fetch(url)
        b64 = base64.b64encode(content).decode("utf-8")
        return f"data:{mime};base64,{b64}"
