from abc import ABC, abstractmethod

from bs4 import BeautifulSoup

class BaseFetcher(ABC):
    """Base class for all fetchers."""

    @abstractmethod
    def fetch(self, url: str) -> str:
        """Fetch the HTML content of the given URL."""
        pass

    def to_soup(self, html: str) -> BeautifulSoup:
        """Convert HTML string to a BeautifulSoup object."""
        return BeautifulSoup(html, "html.parser")
