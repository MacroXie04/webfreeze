import pytest
from fastapi import HTTPException

from webfreeze.server import security
from webfreeze.server.security import assert_proxy_url_allowed


def test_blocks_non_http_scheme():
    with pytest.raises(HTTPException) as e:
        assert_proxy_url_allowed("file:///etc/passwd")
    assert e.value.status_code == 400


def test_blocks_loopback_literal():
    with pytest.raises(HTTPException) as e:
        assert_proxy_url_allowed("http://127.0.0.1/x")
    assert e.value.status_code == 403


def test_blocks_private_literal():
    with pytest.raises(HTTPException) as e:
        assert_proxy_url_allowed("http://192.168.1.10/x")
    assert e.value.status_code == 403


def test_blocks_cloud_metadata():
    with pytest.raises(HTTPException) as e:
        assert_proxy_url_allowed("http://169.254.169.254/latest/meta-data/")
    assert e.value.status_code == 403


def test_blocks_localhost_hostname():
    with pytest.raises(HTTPException) as e:
        assert_proxy_url_allowed("http://localhost:3000/")
    assert e.value.status_code == 403


def test_allows_public_host(monkeypatch):
    monkeypatch.setattr(security, "_resolve_ips", lambda host, port: ["93.184.216.34"])
    assert_proxy_url_allowed("https://example.com/a.css")  # must not raise


def test_blocks_hostname_resolving_to_private(monkeypatch):
    monkeypatch.setattr(security, "_resolve_ips", lambda host, port: ["10.0.0.5"])
    with pytest.raises(HTTPException) as e:
        assert_proxy_url_allowed("https://rebind.example/x")
    assert e.value.status_code == 403


def test_allow_private_env_override(monkeypatch):
    monkeypatch.setenv("WEBFREEZE_ALLOW_PRIVATE", "1")
    assert_proxy_url_allowed("http://127.0.0.1:3000/")  # must not raise
    assert_proxy_url_allowed("http://192.168.0.1/")  # must not raise
