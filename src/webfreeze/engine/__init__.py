from .core import FetchOpts, render_or_fetch
from .jsfidelity import (
    FidelityReport,
    WidgetReport,
    embed_report_comment,
    inline_external_scripts,
    transform_js_fidelity,
)
from .prune import PruneOptions, prune

__all__ = [
    "FetchOpts",
    "render_or_fetch",
    "PruneOptions",
    "prune",
    "FidelityReport",
    "WidgetReport",
    "transform_js_fidelity",
    "inline_external_scripts",
    "embed_report_comment",
]
