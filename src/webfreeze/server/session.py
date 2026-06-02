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
    """Thread-safe ``sid -> Session`` map with a TTL and a size cap.

    Memory is bounded by evicting expired sessions and the oldest entries on
    each insert (no background thread needed); ``get`` also drops expired ones.
    """

    def __init__(self, ttl_seconds: float = 1800, max_sessions: int = 50) -> None:
        self._sessions: Dict[str, Session] = {}
        self._lock = threading.Lock()
        self.ttl_seconds = ttl_seconds
        self.max_sessions = max_sessions

    def new_id(self) -> str:
        return uuid.uuid4().hex

    def save(self, sid: str, session: Session) -> None:
        with self._lock:
            self._evict_locked(now=session.created_at)
            self._sessions[sid] = session
            # Enforce the size cap by dropping the oldest sessions.
            while len(self._sessions) > self.max_sessions:
                oldest = min(self._sessions, key=lambda k: self._sessions[k].created_at)
                del self._sessions[oldest]

    def get(self, sid: str) -> Optional[Session]:
        with self._lock:
            session = self._sessions.get(sid)
            if session is None:
                return None
            if time.time() - session.created_at > self.ttl_seconds:
                del self._sessions[sid]
                return None
            return session

    def _evict_locked(self, now: float) -> int:
        stale = [
            sid for sid, s in self._sessions.items() if now - s.created_at > self.ttl_seconds
        ]
        for sid in stale:
            del self._sessions[sid]
        return len(stale)

    def cleanup(self, ttl_seconds: Optional[float] = None, now: Optional[float] = None) -> int:
        """Evict expired sessions. Returns the count removed."""
        ttl = self.ttl_seconds if ttl_seconds is None else ttl_seconds
        now = time.time() if now is None else now
        with self._lock:
            stale = [sid for sid, s in self._sessions.items() if now - s.created_at > ttl]
            for sid in stale:
                del self._sessions[sid]
        return len(stale)
