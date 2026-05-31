from webfreeze.utils import resolve_url, is_data_uri

def test_resolve_url_absolute():
    assert resolve_url("https://example.com", "https://other.com/a.png") == "https://other.com/a.png"

def test_resolve_url_relative():
    assert resolve_url("https://example.com/dir/", "image.png") == "https://example.com/dir/image.png"
    assert resolve_url("https://example.com/dir/", "/image.png") == "https://example.com/image.png"

def test_resolve_url_data_uri():
    data = "data:image/png;base64,xxxx"
    assert resolve_url("https://example.com", data) == data

def test_is_data_uri():
    assert is_data_uri("data:text/plain,hello") is True
    assert is_data_uri("https://example.com") is False
    assert is_data_uri("/path/to/file") is False
