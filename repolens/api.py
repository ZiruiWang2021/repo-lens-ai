from __future__ import annotations

from pathlib import Path

from repolens import db
from repolens.agent import RepoLensAgent
from repolens.config import Settings
from repolens.indexer import RepositoryIndexer
from repolens.providers import provider_from_settings

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel
except ImportError as exc:  # pragma: no cover
    FastAPI = None  # type: ignore[assignment]
    HTTPException = None  # type: ignore[assignment]
    FileResponse = None  # type: ignore[assignment]
    StaticFiles = None  # type: ignore[assignment]
    BaseModel = object  # type: ignore[assignment,misc]
    FASTAPI_IMPORT_ERROR = exc
else:
    FASTAPI_IMPORT_ERROR = None


if BaseModel is object:  # pragma: no cover
    class IndexRequest:  # type: ignore[no-redef]
        pass

    class ChatRequest:  # type: ignore[no-redef]
        pass

    class ReviewRequest:  # type: ignore[no-redef]
        pass
else:
    class IndexRequest(BaseModel):
        source: str

    class ChatRequest(BaseModel):
        question: str
        repo_id: int | None = None
        limit: int = 6

    class ReviewRequest(BaseModel):
        diff: str


def create_app(settings: Settings | None = None):
    if FastAPI is None:  # pragma: no cover
        raise RuntimeError("FastAPI is not installed. Run: pip install -e .") from FASTAPI_IMPORT_ERROR

    settings = settings or Settings.from_env()
    app = FastAPI(
        title="RepoLens AI",
        version="0.1.0",
        description="Index code repositories, ask cited questions, review diffs, and expose MCP tools.",
    )
    web_dir = Path(__file__).parent / "web"

    @app.post("/api/repos/index")
    def index_repo(request: IndexRequest) -> dict[str, object]:
        try:
            summary = RepositoryIndexer(settings.db_path).index(request.source)
            return summary.__dict__
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/chat")
    def chat(request: ChatRequest) -> dict[str, object]:
        connection = db.connect(settings.db_path)
        try:
            agent = RepoLensAgent(connection, provider_from_settings(settings))
            return agent.ask(request.question, request.repo_id, request.limit).to_dict()
        finally:
            connection.close()

    @app.post("/api/review")
    def review(request: ReviewRequest) -> dict[str, object]:
        connection = db.connect(settings.db_path)
        try:
            agent = RepoLensAgent(connection, provider_from_settings(settings))
            return agent.review_diff(request.diff).to_dict()
        finally:
            connection.close()

    @app.get("/api/repos/{repo_id}/map")
    def get_repo_map(repo_id: int) -> dict[str, object]:
        connection = db.connect(settings.db_path)
        try:
            try:
                return db.repo_map(connection, repo_id)
            except KeyError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
        finally:
            connection.close()

    @app.get("/")
    def root():
        return FileResponse(web_dir / "index.html")

    app.mount("/static", StaticFiles(directory=web_dir), name="static")
    return app


app = create_app() if FastAPI is not None else None
