from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from api.routes import sync as sync_routes


def create_app() -> FastAPI:
    app = FastAPI(
        title="Video Sync API",
        description="REST API wrapping core/video_editor.py for side-by-side sync.",
        version="0.1.0",
    )
    app.include_router(sync_routes.router)

    @app.get("/", include_in_schema=False)
    async def redirect_to_docs() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    return app


app = create_app()
