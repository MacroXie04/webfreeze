"""Console entry point: ``webfreeze-serve``.

Launches the local FastAPI service. P5 adds browser auto-open, session TTL, and
serving the built React assets.
"""

import click


@click.command()
@click.option("--host", default="127.0.0.1", help="Bind address (local only).")
@click.option("--port", default=8000, type=int, help="Port to listen on.")
@click.option("--reload", is_flag=True, help="Auto-reload on code changes (dev).")
def serve(host: str, port: int, reload: bool) -> None:
    """Start the webfreeze visual-picker backend."""
    import uvicorn

    uvicorn.run(
        "webfreeze.server.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    serve()
