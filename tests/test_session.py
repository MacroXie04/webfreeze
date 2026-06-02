import time

from bs4 import BeautifulSoup

from webfreeze.server.session import Session, SessionStore


def _session(created_at):
    soup = BeautifulSoup("<html></html>", "html.parser")
    return Session(
        soup=soup,
        soup_preview=soup,
        base_url="",
        origin="",
        cache=None,
        title="t",
        created_at=created_at,
    )


def test_get_returns_fresh_session():
    store = SessionStore(ttl_seconds=1000)
    sid = store.new_id()
    store.save(sid, _session(time.time()))
    assert store.get(sid) is not None


def test_get_evicts_expired_session():
    store = SessionStore(ttl_seconds=5)
    sid = store.new_id()
    store.save(sid, _session(time.time() - 10))
    assert store.get(sid) is None


def test_size_cap_evicts_oldest():
    store = SessionStore(ttl_seconds=10000, max_sessions=2)
    now = time.time()
    s1, s2, s3 = store.new_id(), store.new_id(), store.new_id()
    store.save(s1, _session(now - 3))
    store.save(s2, _session(now - 2))
    store.save(s3, _session(now - 1))  # over cap -> oldest (s1) dropped
    assert store.get(s1) is None
    assert store.get(s2) is not None
    assert store.get(s3) is not None
