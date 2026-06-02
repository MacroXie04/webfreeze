from unittest.mock import MagicMock

from bs4 import BeautifulSoup

from webfreeze.cache import ResourceCache
from webfreeze.engine import (
    FidelityReport,
    embed_report_comment,
    inline_external_scripts,
    transform_js_fidelity,
)


def _soup(html):
    return BeautifulSoup(html, "html.parser")


def test_off_mode_is_noop():
    soup = _soup(
        '<html><body><button aria-expanded="false" aria-controls="p">X</button>'
        '<div id="p">c</div></body></html>'
    )
    report = transform_js_fidelity(soup, "off")
    assert soup.find("details") is None
    assert report.widgets == []


def test_disclosure_to_details_closed():
    soup = _soup(
        '<html><body><button aria-expanded="false" aria-controls="p">Toggle</button>'
        '<div id="p" hidden>Panel body</div></body></html>'
    )
    report = transform_js_fidelity(soup, "css")
    details = soup.find("details")
    assert details is not None
    assert not details.has_attr("open")
    assert details.find("summary").get_text() == "Toggle"
    assert "Panel body" in details.get_text()
    assert soup.find("button") is None
    assert any(w.type == "disclosure" for w in report.widgets)


def test_disclosure_open_from_aria_expanded():
    soup = _soup(
        '<html><body><button aria-expanded="true" aria-controls="p">Toggle</button>'
        '<div id="p">Panel</div></body></html>'
    )
    transform_js_fidelity(soup, "css")
    assert soup.find("details").has_attr("open")


def test_tabs_to_radio_checked_hack():
    soup = _soup(
        "<html><head></head><body>"
        '<div role="tablist">'
        '<button role="tab" aria-selected="true" aria-controls="t1">Tab1</button>'
        '<button role="tab" aria-controls="t2">Tab2</button>'
        "</div>"
        '<div role="tabpanel" id="t1">Panel1</div>'
        '<div role="tabpanel" id="t2">Panel2</div>'
        "</body></html>"
    )
    report = transform_js_fidelity(soup, "css")

    radios = soup.find_all("input", {"type": "radio"})
    assert len(radios) == 2
    assert radios[0].has_attr("checked")  # aria-selected="true" on Tab1
    assert not radios[1].has_attr("checked")

    labels = soup.find_all("label", {"class": "wf-tab-label"})
    assert labels[0].get_text() == "Tab1"
    assert len(soup.select(".wf-tab-panel")) == 2

    style = soup.find("style", {"data-wf": "tier1"})
    assert style is not None and ":checked" in style.string
    assert soup.find(attrs={"role": "tablist"}) is None
    assert any(w.type == "tabs" for w in report.widgets)


def test_tabs_default_first_checked_when_none_selected():
    soup = _soup(
        "<html><head></head><body>"
        '<div role="tablist">'
        '<button role="tab" aria-controls="t1">A</button>'
        '<button role="tab" aria-controls="t2">B</button>'
        "</div>"
        '<div role="tabpanel" id="t1">1</div>'
        '<div role="tabpanel" id="t2">2</div>'
        "</body></html>"
    )
    transform_js_fidelity(soup, "css")
    radios = soup.find_all("input", {"type": "radio"})
    assert radios[0].has_attr("checked")


def test_inline_external_scripts_keeps_and_inlines():
    soup = _soup(
        '<html><body><script src="/app.js"></script>'
        "<script>inlineCode()</script></body></html>"
    )
    cache = MagicMock(spec=ResourceCache)
    cache.fetch.return_value = ("application/javascript", b"console.log('external')")
    report = FidelityReport()
    inline_external_scripts(soup, cache, "https://example.com/", report)

    scripts = soup.find_all("script")
    assert len(scripts) == 2
    assert all(not s.get("src") for s in scripts)  # external src inlined + removed
    assert any("console.log('external')" in (s.string or "") for s in scripts)
    assert report.kept_scripts == 2
    assert all(w.strategy == "kept-js" for w in report.widgets)


def test_inline_external_scripts_survives_fetch_failure():
    soup = _soup('<html><body><script src="/x.js"></script></body></html>')
    cache = MagicMock(spec=ResourceCache)
    cache.fetch.side_effect = RuntimeError("boom")
    report = FidelityReport()
    inline_external_scripts(soup, cache, "https://example.com/", report)
    assert report.kept_scripts == 1
    assert "requires network" in report.widgets[0].note


def test_embed_report_comment():
    soup = _soup("<html><head></head><body></body></html>")
    report = FidelityReport()
    report.kept_scripts = 2
    embed_report_comment(soup, report)
    out = str(soup)
    assert "webfreeze fidelity report" in out
    assert '"keptScripts":2' in out
