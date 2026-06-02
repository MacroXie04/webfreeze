"""HP4 Tier-1 — convert common JS-driven widgets to pure CSS so the export still
works offline with zero JS.

Recognized patterns (conservative, ARIA-based):
  - disclosure/accordion: <button aria-expanded aria-controls="id"> + panel
        -> <details>/<summary> (open state read from the live DOM)
  - tabs:                  [role=tablist] of [role=tab aria-controls] + panels
        -> radio :checked hack with scoped, wf-prefixed CSS

Initial open/active state is taken from the captured (post-interaction) DOM.
Everything else is left as-is; Tier-2 keep-JS (P4) is the fallback.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from bs4 import BeautifulSoup, Tag


@dataclass
class WidgetReport:
    selector: str
    type: str  # disclosure | tabs | js-animation | unknown
    strategy: str  # css | kept-js | flattened | native
    confidence: float
    note: str

    def to_dict(self) -> dict:
        return {
            "selector": self.selector,
            "type": self.type,
            "strategy": self.strategy,
            "confidence": self.confidence,
            "note": self.note,
        }


@dataclass
class FidelityReport:
    widgets: List[WidgetReport] = field(default_factory=list)
    kept_scripts: int = 0
    size_kb: int = 0

    def to_dict(self) -> dict:
        return {
            "widgets": [w.to_dict() for w in self.widgets],
            "keptScripts": self.kept_scripts,
            "sizeKB": self.size_kb,
        }


def _selector(el: Tag) -> str:
    sel = el.name
    if el.get("id"):
        sel += "#" + el["id"]
    elif el.get("class"):
        sel += "." + ".".join(el["class"][:2])
    return sel


def _is_visible(el: Tag) -> bool:
    if el.has_attr("hidden"):
        return False
    if "display:none" in el.get("style", "").replace(" ", ""):
        return False
    return True


def _move_children(src: Tag, dst: Tag) -> None:
    for child in list(src.contents):
        dst.append(child.extract())


def _convert_disclosures(soup: BeautifulSoup, report: FidelityReport) -> None:
    triggers = soup.find_all(attrs={"aria-controls": True, "aria-expanded": True})
    for trigger in triggers:
        panel = soup.find(id=trigger.get("aria-controls"))
        if panel is None or panel is trigger or trigger in panel.parents:
            continue

        is_open = trigger.get("aria-expanded") == "true" or _is_visible(panel)

        details = soup.new_tag("details")
        if is_open:
            details["open"] = ""
        summary = soup.new_tag("summary")
        _move_children(trigger, summary)
        details.append(summary)

        trigger.insert_before(details)
        panel.attrs.pop("hidden", None)  # CSS/details now controls visibility
        details.append(panel.extract())
        trigger.decompose()

        report.widgets.append(
            WidgetReport(
                _selector(details),
                "disclosure",
                "css",
                0.85,
                "aria-controls -> <details%s>" % (" open" if is_open else ""),
            )
        )


def _convert_tabs(soup: BeautifulSoup, report: FidelityReport, counter: List[int]) -> None:
    for tablist in soup.find_all(attrs={"role": "tablist"}):
        pairs = []
        for tab in tablist.find_all(attrs={"role": "tab"}):
            pid = tab.get("aria-controls")
            panel = soup.find(id=pid) if pid else None
            if panel is not None:
                pairs.append((tab, panel))
        if len(pairs) < 2:
            continue

        gid = "wf-tabs%d" % counter[0]
        counter[0] += 1
        container = soup.new_tag("div", attrs={"class": "wf-tabs", "id": gid})
        css = ["#%s .wf-tab-panel{display:none}" % gid]
        any_checked = False

        for i, (tab, _panel) in enumerate(pairs):
            in_id = "%s-%d" % (gid, i)
            inp = soup.new_tag(
                "input",
                attrs={"type": "radio", "name": gid, "id": in_id, "class": "wf-tab-input"},
            )
            if tab.get("aria-selected") == "true":
                inp["checked"] = ""
                any_checked = True
            label = soup.new_tag("label", attrs={"for": in_id, "class": "wf-tab-label"})
            _move_children(tab, label)
            container.append(inp)
            container.append(label)
            css.append(
                '#%s:checked ~ .wf-tab-panel[data-wf-tab="%d"]{display:block}' % (in_id, i)
            )

        if not any_checked:
            container.find("input")["checked"] = ""

        for i, (_tab, panel) in enumerate(pairs):
            moved = panel.extract()
            classes = moved.get("class") or []
            if isinstance(classes, str):
                classes = classes.split()
            moved["class"] = classes + ["wf-tab-panel"]
            moved["data-wf-tab"] = str(i)
            container.append(moved)

        tablist.insert_before(container)
        tablist.decompose()

        style = soup.new_tag("style")
        style["data-wf"] = "tier1"
        style.string = "".join(css)
        (soup.head or soup).append(style)

        report.widgets.append(
            WidgetReport("#" + gid, "tabs", "css", 0.7, "%d tabs -> radio :checked" % len(pairs))
        )


def transform_js_fidelity(
    soup: BeautifulSoup, mode: str, cache: Optional[object] = None
) -> FidelityReport:
    """Apply Tier-1 CSS conversions in place. ``mode`` in {off, css, css+js}.

    ``cache`` is accepted for the P4 Tier-2 path (external <script> inlining) and
    is unused by Tier-1.
    """
    report = FidelityReport()
    if mode not in ("css", "css+js"):
        return report
    _convert_tabs(soup, report, [0])
    _convert_disclosures(soup, report)
    return report
