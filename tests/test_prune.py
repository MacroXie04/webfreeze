from bs4 import BeautifulSoup

from webfreeze.engine import PruneOptions, prune


def _soup(html):
    return BeautifulSoup(html, "html.parser")


def test_empty_selection_is_noop():
    soup = _soup("<html><body><div>a</div><div>b</div></body></html>")
    prune(soup)
    assert len(soup.find_all("div")) == 2


def test_keeps_selected_branch_and_drops_siblings():
    soup = _soup(
        '<html><head><style>x</style></head><body>'
        '<div class="keep" data-wf-keep="w1"><p>hi</p></div>'
        '<div class="other">bye</div></body></html>'
    )
    prune(soup)
    assert soup.find("div", class_="keep") is not None
    assert soup.find("div", class_="other") is None
    assert soup.find("p").get_text() == "hi"
    assert soup.find("style") is not None  # <head> preserved
    assert soup.select("[data-wf-keep]") == []  # markers stripped


def test_ancestor_chain_retained():
    soup = _soup(
        '<html><body><section class="container">'
        '<div class="row"><span data-wf-keep="w1">x</span></div>'
        '<div class="row2">drop</div></section>'
        "<aside>drop2</aside></body></html>"
    )
    prune(soup)
    assert soup.find("section", class_="container") is not None
    assert soup.find("div", class_="row") is not None
    assert soup.find("span").get_text() == "x"
    assert soup.find("div", class_="row2") is None
    assert soup.find("aside") is None


def test_disjoint_multiselect_union():
    soup = _soup(
        '<html><body><div id="a" data-wf-keep="w1">A</div>'
        '<div id="mid">M</div>'
        '<div id="b" data-wf-keep="w2">B</div></body></html>'
    )
    prune(soup)
    assert soup.find(id="a") is not None
    assert soup.find(id="b") is not None
    assert soup.find(id="mid") is None


def test_descendants_of_keep_untouched():
    soup = _soup(
        '<html><body><div data-wf-keep="w1"><ul><li>1</li><li>2</li></ul></div>'
        '<div class="x">drop</div></body></html>'
    )
    prune(soup)
    assert len(soup.find_all("li")) == 2
    assert soup.find("div", class_="x") is None


def test_hide_mode_keeps_siblings_hidden():
    soup = _soup(
        '<html><body><div data-wf-keep="w1">keep</div>'
        '<div class="sib">sib</div></body></html>'
    )
    prune(soup, PruneOptions(strip_unselected_siblings=False))
    sib = soup.find("div", class_="sib")
    assert sib is not None
    assert "display:none" in sib.get("style", "")
