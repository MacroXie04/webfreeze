from bs4 import BeautifulSoup

from webfreeze.utils import resolve_url, is_data_uri, dumps_html, neutralize_scripts

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

def test_dumps_html_adds_doctype():
    soup = BeautifulSoup("<html><body><p>hi</p></body></html>", "html.parser")
    assert dumps_html(soup).startswith("<!DOCTYPE html>\n")

def test_dumps_html_preserves_existing_doctype():
    soup = BeautifulSoup("<!DOCTYPE html>\n<html><body>x</body></html>", "html.parser")
    assert dumps_html(soup).lower().count("<!doctype") == 1

def test_dumps_html_no_escape_in_script():
    soup = BeautifulSoup(
        "<html><body><script>if (a < b && c > d) {}</script></body></html>",
        "html.parser",
    )
    out = dumps_html(soup)
    assert "a < b && c > d" in out
    assert "&amp;" not in out
    assert "&lt;" not in out

def test_neutralize_strip_all():
    soup = BeautifulSoup(
        '<html><body><script>x</script><div onclick="y()">z</div>'
        "<noscript>n</noscript></body></html>",
        "html.parser",
    )
    neutralize_scripts(soup, "strip_all")
    assert soup.find("script") is None
    assert soup.find("noscript") is None
    assert not soup.find("div").has_attr("onclick")

def test_neutralize_keep_all_is_noop():
    soup = BeautifulSoup("<html><body><script>x</script></body></html>", "html.parser")
    neutralize_scripts(soup, "keep_all")
    assert soup.find("script") is not None

def test_neutralize_keep_flagged():
    soup = BeautifulSoup(
        "<html><body><script data-wf-keep-script>keep</script>"
        "<script>drop</script></body></html>",
        "html.parser",
    )
    neutralize_scripts(soup, "keep_flagged")
    scripts = soup.find_all("script")
    assert len(scripts) == 1
    assert "keep" in scripts[0].text
