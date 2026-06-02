"""FastAPI application factory for the webfreeze visual picker (P1).

Endpoints: /api/health, /api/session, /api/session/{id}/preview, /proxy,
/api/freeze. Picking/pruning (P2) and JS-fidelity transforms (P3/P4) are not yet
wired; /api/freeze currently does whole-page (or grabbed-DOM) inlining only.
"""

from typing import Optional
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from ..cache import ResourceCache
from ..engine import FetchOpts, PruneOptions, prune, render_or_fetch
from ..inliner import Inliner
from ..utils import dumps_html
from .preview import proxy_url, rewrite_for_preview, unrewrite_proxy_urls
from .session import Session, SessionStore


class SessionRequest(BaseModel):
    url: str
    mode: str = "auto"
    waitFor: Optional[str] = None
    scroll: bool = True


class FreezeOptions(BaseModel):
    inlineImages: bool = True
    jsFidelity: str = "off"  # "off" | "css" | "css+js" (css/css+js arrive in P3/P4)
    stripUnselectedSiblings: bool = True


class FreezeRequest(BaseModel):
    sessionId: str
    domHtml: Optional[str] = None
    keep: str = "selection"  # "selection" | "whole"
    options: FreezeOptions = Field(default_factory=FreezeOptions)


def _version() -> str:
    try:
        from importlib.metadata import version

        return version("webfreeze")
    except Exception:
        return "0.1.0"


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}" if parts.scheme else ""


def _neutralize_scripts(soup: BeautifulSoup) -> None:
    """Strip scripts / on* handlers / <noscript> — the CLI's default export shape.

    Used when jsFidelity == "off". P4 unifies this with RenderedFetcher's policy.
    """
    for script in soup.find_all("script"):
        script.decompose()
    for tag in soup.find_all(True):
        for attr in [a for a in list(tag.attrs) if a.lower().startswith("on")]:
            del tag[attr]
    for noscript in soup.find_all("noscript"):
        noscript.decompose()


def create_app(store: Optional[SessionStore] = None) -> FastAPI:
    app = FastAPI(title="webfreeze")
    store = store or SessionStore()
    app.state.store = store

    # Dev-only: allow the Vite dev server origin. The service itself binds to
    # 127.0.0.1 (see server/cli.py).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": _version()}

    @app.post("/api/session")
    def create_session(req: SessionRequest):
        cache = ResourceCache()
        opts = FetchOpts(
            wait_for=req.waitFor,
            scroll=req.scroll,
            script_policy="keep_all",  # keep JS so the preview stays interactive
        )
        try:
            soup, base_url = render_or_fetch(req.url, req.mode, opts, cache)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Failed to load page: {e}")

        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else req.url

        sid = store.new_id()
        # Separate preview soup (deep copy via re-parse) so the original is kept
        # intact for keep="whole" exports.
        preview = BeautifulSoup(dumps_html(soup), "html.parser")
        rewrite_for_preview(preview, base_url, sid, cache)

        store.save(
            sid,
            Session(
                soup=soup,
                soup_preview=preview,
                base_url=base_url,
                origin=_origin(req.url),
                cache=cache,
                title=title,
            ),
        )
        return {
            "sessionId": sid,
            "previewUrl": f"/api/session/{sid}/preview",
            "title": title,
            "renderMode": "static" if req.mode == "static" else "render",
            "warnings": [
                "Runtime fetch/XHR fired during interaction is not proxied yet (P3).",
            ],
        }

    @app.get("/api/session/{sid}/preview", response_class=HTMLResponse)
    def get_preview(sid: str):
        session = store.get(sid)
        if session is None:
            raise HTTPException(status_code=404, detail="Unknown session")
        return HTMLResponse(content=dumps_html(session.soup_preview))

    @app.get("/proxy")
    def proxy(url: str, sid: str):
        session = store.get(sid)
        if session is None:
            raise HTTPException(status_code=404, detail="Unknown session")
        # Minimal scheme guard; full SSRF allowlist (same-site + private-range
        # blocking) lands in P5/HP5.
        if not url.lower().startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="Unsupported URL scheme")
        try:
            mime, content = session.cache.fetch(url)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Proxy fetch failed: {e}")

        # Rewrite nested url()/@import in proxied CSS so they also route through
        # /proxy when the browser resolves them.
        if mime.startswith("text/css"):
            css = Inliner(session.cache).inline_css(
                content.decode("utf-8", errors="replace"),
                url,
                url_target=lambda u: proxy_url(u, sid),
            )
            return Response(content=css, media_type="text/css")
        return Response(content=content, media_type=mime)

    @app.post("/api/freeze")
    def freeze(req: FreezeRequest):
        session = store.get(req.sessionId)
        if session is None:
            raise HTTPException(status_code=404, detail="Unknown session")

        if req.keep == "whole" or not req.domHtml:
            # Re-parse so the stored original is never mutated.
            soup = BeautifulSoup(dumps_html(session.soup), "html.parser")
        else:
            soup = BeautifulSoup(req.domHtml, "html.parser")
            unrewrite_proxy_urls(soup)
            prune(
                soup,
                PruneOptions(
                    strip_unselected_siblings=req.options.stripUnselectedSiblings
                ),
            )
            # P3/P4: jsFidelity transforms run here, after prune.

        if req.options.jsFidelity == "off":
            _neutralize_scripts(soup)

        Inliner(session.cache, inline_images=req.options.inlineImages).process_soup(
            soup, session.base_url
        )
        html = dumps_html(soup)
        return {
            "html": html,
            "report": {
                "sizeKB": len(html.encode("utf-8")) // 1024,
                "keptScripts": len(soup.find_all("script")),
                "widgets": [],
            },
        }

    return app
