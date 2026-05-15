from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import inspection_ui_path, router
from app.repositories.json_store import JsonStudyRepository
from app.services.pipeline import StudyPipeline
from app.services.session_flow import SessionManager


def create_app(
    *,
    repository: JsonStudyRepository | None = None,
    pipeline: StudyPipeline | None = None,
) -> FastAPI:
    app = FastAPI(title="StudyFlow AI", version="0.1.0")
    app.state.repository = repository or JsonStudyRepository(
        Path("data") / "study_data.json"
    )
    app.state.pipeline = pipeline or StudyPipeline()
    app.state.session_manager = SessionManager()
    app.include_router(router)
    app.mount(
        "/static",
        StaticFiles(directory=Path(__file__).resolve().parent / "static"),
        name="static",
    )

    @app.get("/", include_in_schema=False)
    def home():
        return FileResponse(Path(__file__).resolve().parent / "static" / "index.html")

    @app.get("/inspection", include_in_schema=False)
    def inspection():
        return FileResponse(inspection_ui_path())

    return app


app = create_app()
