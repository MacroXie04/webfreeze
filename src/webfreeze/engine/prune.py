"""HP3 — prune a captured DOM down to the user's selection.

Selected elements are marked with ``data-wf-keep`` by the picker. We retain each
keep node, all of its descendants, and all of its ancestors (so descendant/child
CSS selectors like ``.container > .row .card`` keep matching), and drop (or hide)
the unselected sibling branches along the ancestor chain. ``<head>`` is always
kept whole so styles survive.
"""

from dataclasses import dataclass
from typing import Optional

from bs4 import BeautifulSoup, Tag


@dataclass
class PruneOptions:
    # True  -> decompose unselected siblings (smallest fragment, default)
    # False -> keep them but display:none (preserves nth-child/sibling layouts)
    strip_unselected_siblings: bool = True


def prune(soup: BeautifulSoup, options: Optional[PruneOptions] = None) -> None:
    """Prune `soup` in place to the ``data-wf-keep`` selection. No-op if empty."""
    options = options or PruneOptions()

    keep_nodes = soup.select("[data-wf-keep]")
    if not keep_nodes:
        return  # whole-page fallback / back-compat

    retain: set[int] = set()
    ancestor_tags: list[Tag] = []
    seen_ancestors: set[int] = set()

    for node in keep_nodes:
        retain.add(id(node))
        for desc in node.descendants:
            if isinstance(desc, Tag):
                retain.add(id(desc))
        for anc in node.parents:
            if isinstance(anc, Tag):
                retain.add(id(anc))
                if id(anc) not in seen_ancestors:
                    seen_ancestors.add(id(anc))
                    ancestor_tags.append(anc)

    # Always keep <head> entirely (styles/base/meta live there).
    head = soup.find("head")
    if head is not None:
        retain.add(id(head))
        for desc in head.descendants:
            if isinstance(desc, Tag):
                retain.add(id(desc))

    # Along each ancestor of a keep node, drop/hide children not on a retain path.
    for anc in ancestor_tags:
        for child in list(anc.find_all(recursive=False)):
            if id(child) in retain:
                continue
            if options.strip_unselected_siblings:
                child.decompose()
            else:
                existing = child.get("style", "")
                child["style"] = (existing + ";display:none !important").lstrip(";")

    # Cleanup: drop the markers and any leftover picker UI nodes.
    for node in soup.select("[data-wf-keep]"):
        del node["data-wf-keep"]
    for ui in soup.select("[data-wf-ui]"):
        ui.decompose()
