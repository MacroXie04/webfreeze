"""Console entry point: ``webfreeze-serve``.

Launches the local FastAPI service and (by default) opens the browser. Serves
the built React UI when present; otherwise the API still works behind a Vite
dev server.
"""

import threading
import webbrowser

import click

from .app import STATIC_DIR


@click.command()
@click.option("--host", default="127.0.0.1", help="Bind address (local only).")
@click.option("--port", default=8000, type=int, help="Port to listen on.")
@click.option("--reload", is_flag=True, help="Auto-reload on code changes (dev).")
@click.option("--open/--no-open", "open_browser", default=True, help="Open the browser on start.")
def serve(host: str, port: int, reload: bool, open_browser: bool) -> None:
    """Start the webfreeze visual-picker backend."""
    import uvicorn

    url = f"http://{host}:{port}/"
    if not STATIC_DIR.is_dir():
        click.echo(
            "[!] UI assets not built — the API is up but '/' has no page.\n"
            "    Build the frontend:  npm --prefix web install && npm --prefix web run build\n"
            "    Or run the Vite dev server:  npm --prefix web run dev",
            err=True,
        )
    elif open_browser and not reload:
        # Open once the server is accepting connections (reload spawns a child,
        # so skip auto-open there to avoid double tabs).
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    uvicorn.run(
        "webfreeze.server.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    serve()
