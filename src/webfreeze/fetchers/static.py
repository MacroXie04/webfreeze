import requests

from .base import BaseFetcher

class StaticFetcher(BaseFetcher):
    """Fetcher that uses the requests library for fast, static HTML retrieval."""

    def __init__(self, session: requests.Session):
        self.session = session

    def fetch(self, url: str) -> str:
        """Fetch the HTML content using requests."""
        response = self.session.get(url, timeout=20)
        response.raise_for_status()
        
        # Detect encoding automatically
        response.encoding = response.apparent_encoding
        return response.text
