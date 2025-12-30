from __future__ import annotations

from fastapi import FastAPI

from api.routes import sync as sync_routes


def create_app() -> FastAPI:
    app = FastAPI(
        title="Video Sync API",
        description="REST API wrapping core/video_editor.py for side-by-side sync.",
        version="0.1.0",
    )
    app.include_router(sync_routes.router)
    return app


app = create_app()
