import pytest
from unittest.mock import MagicMock
from webfreeze.cache import ResourceCache

def test_cache_fetch_success():
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "text/css"}
    mock_response.content = b"body { color: red; }"
    mock_session.get.return_value = mock_response
    
    cache = ResourceCache(session=mock_session)
    mime, content = cache.fetch("https://example.com/style.css")
    
    assert mime == "text/css"
    assert content == b"body { color: red; }"
    assert mock_session.get.call_count == 1
    
    # Second fetch should be from cache
    mime2, content2 = cache.fetch("https://example.com/style.css")
    assert mime2 == "text/css"
    assert content2 == b"body { color: red; }"
    assert mock_session.get.call_count == 1

def test_cache_fetch_failure():
    mock_session = MagicMock()
    mock_session.get.side_effect = Exception("Network error")
    
    cache = ResourceCache(session=mock_session)
    with pytest.raises(RuntimeError, match="Failed to fetch"):
        cache.fetch("https://example.com/fail.css")

def test_cache_fetch_base64():
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.headers = {"Content-Type": "image/png"}
    mock_response.content = b"fake-binary"
    mock_session.get.return_value = mock_response
    
    cache = ResourceCache(session=mock_session)
    data_uri = cache.fetch_base64("https://example.com/img.png")
    
    assert data_uri.startswith("data:image/png;base64,")
    assert "ZmFrZS1iaW5hcnk=" in data_uri # base64 for 'fake-binary'
