"""In-memory capture-session store.

Each session holds the rendered page (original + preview-rewritten) and its own
``ResourceCache`` so concurrent sessions never share a requests.Session. TTL /
size-cap eviction is stubbed here and implemented in P5.
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional

from bs4 import BeautifulSoup

from ..cache import ResourceCache


@dataclass
class Session:
    soup: BeautifulSoup           # original, un-rewritten — used for keep="whole"
    soup_preview: BeautifulSoup   # rewritten so resources point at /proxy
    base_url: str
    origin: str                   # scheme://host of the original page (SSRF basis, P5)
    cache: ResourceCache
    title: str
    created_at: float = field(default_factory=time.time)


class SessionStore:
    """Thread-safe ``sid -> Session`` map."""

    def __init__(self) -> None:
        self._sessions: Dict[str, Session] = {}
        self._lock = threading.Lock()

    def new_id(self) -> str:
        return uuid.uuid4().hex

    def save(self, sid: str, session: Session) -> None:
        with self._lock:
            self._sessions[sid] = session

    def get(self, sid: str) -> Optional[Session]:
        with self._lock:
            return self._sessions.get(sid)

    def cleanup(self, ttl_seconds: float, now: Optional[float] = None) -> int:
        """Evict sessions older than ttl_seconds. Returns the count removed. (P5)"""
        now = time.time() if now is None else now
        with self._lock:
            stale = [
                sid
                for sid, s in self._sessions.items()
                if now - s.created_at > ttl_seconds
            ]
            for sid in stale:
                del self._sessions[sid]
        return len(stale)
