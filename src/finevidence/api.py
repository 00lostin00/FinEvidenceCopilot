import mimetypes
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from .charts import render_svg
from .finance import METRIC_NAMES
from .models import AskRequest, AskResponse
from .service import Copilot

mimetypes.add_type("image/svg+xml", ".svg")


def create_app(project_root: Path | None = None, copilot: Copilot | None = None) -> FastAPI:
    root = project_root or Path(os.getenv("FINEVIDENCE_ROOT", Path(__file__).resolve().parents[2]))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        provider = os.getenv("FINEVIDENCE_PROVIDER", "offline")
        if provider not in {"offline", "llm"}:
            raise ValueError("FINEVIDENCE_PROVIDER must be offline or llm")
        app.state.copilot = copilot or Copilot(root, provider=provider)
        app.state.capacity = threading.BoundedSemaphore(4)
        yield

    app = FastAPI(title="FinEvidence Copilot", version="0.1.0", lifespan=lifespan)
    web_root = Path(__file__).resolve().parent / "web"
    app.mount("/static", StaticFiles(directory=web_root), name="static")

    @app.get("/", include_in_schema=False)
    def workbench() -> FileResponse:
        return FileResponse(web_root / "index.html", headers={"Cache-Control": "no-cache"})

    @app.middleware("http")
    async def browser_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if request.url.path == "/" or request.url.path.startswith("/static/"):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "img-src 'self' blob:; connect-src 'self'; object-src 'none'; "
                "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
            )
        return response

    @app.get("/v1/catalog")
    def catalog(request: Request) -> dict:
        service = request.app.state.copilot
        documents = {chunk.source: chunk.title for chunk in service.index.chunks}
        return {
            "dataset_version": service.store.version,
            "fictional": True,
            "unit": service.store.unit,
            "provider": service.provider,
            "companies": [
                {"id": company, "name": name} for company, name in service.store.names.items()
            ],
            "years": sorted({year for _, year in service.store.rows}),
            "record_count": len(service.store.rows),
            "chunk_count": len(service.index.chunks),
            "documents": [
                {"source": source, "title": title} for source, title in documents.items()
            ],
            "metrics": [{"id": metric, "name": name} for metric, name in METRIC_NAMES.items()],
        }

    @app.get("/health")
    def health(request: Request) -> dict[str, str]:
        return {
            "status": "ok",
            "provider": request.app.state.copilot.provider,
            "dataset_version": request.app.state.copilot.store.version,
        }

    @app.post("/v1/ask", response_model=AskResponse)
    def ask(payload: AskRequest, request: Request) -> AskResponse:
        if not request.app.state.capacity.acquire(blocking=False):
            raise HTTPException(429, "服务忙，请重试", headers={"Retry-After": "2"})
        try:
            return request.app.state.copilot.ask(payload.question)
        finally:
            request.app.state.capacity.release()

    @app.post("/v1/chart.svg")
    def chart(payload: AskRequest, request: Request) -> Response:
        result = ask(payload, request)
        if result.chart is None:
            raise HTTPException(422, "请提供包含图表意图、公司及年度的单指标问题")
        return Response(render_svg(result.chart), media_type="image/svg+xml")

    return app


app = create_app()
