from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import SESSION_COOKIE_NAME, inspection_ui_path, require_inspection_access, router
from app.config import get_studyflow_data_file, get_studyflow_upload_root
from app.repositories.json_store import JsonStudyRepository
from app.services.pipeline import StudyPipeline
from app.services.session_flow import SessionManager


def create_app(
    *,
    repository: JsonStudyRepository | None = None,
    pipeline: StudyPipeline | None = None,
) -> FastAPI:
    app = FastAPI(title="StudyFlow AI", version="0.1.0")
    app.state.repository = repository or JsonStudyRepository(get_studyflow_data_file())
    app.state.pipeline = pipeline or StudyPipeline()
    app.state.session_manager = SessionManager()
    app.state.auth_sessions = {}
    default_upload_root = app.state.repository.path.parent / "uploads"
    app.state.storage_root = get_studyflow_upload_root(default_upload_root)
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
    def inspection(request: Request):
        require_inspection_access(request)
        return FileResponse(inspection_ui_path())

    @app.get("/dashboard", include_in_schema=False)
    def dashboard(request: Request):
        token = request.cookies.get(SESSION_COOKIE_NAME)
        user_id = request.app.state.auth_sessions.get(token) if token else None
        user = app.state.repository.get_user(user_id) if user_id else None
        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail="Authentication required.")
        return FileResponse(Path(__file__).resolve().parent / "static" / "dashboard.html")

    return app


app = create_app()
