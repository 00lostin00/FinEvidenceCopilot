import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response

from .charts import render_svg
from .models import AskRequest, AskResponse
from .service import Copilot


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
