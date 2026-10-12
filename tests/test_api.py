import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from finevidence.api import create_app
from finevidence.models import QueryPlan


def test_api_json_and_svg(copilot):
    with TestClient(create_app(copilot=copilot)) as client:
        response = client.post("/v1/ask", json={"question": "青禾科技2025年营业收入"})
        assert response.status_code == 200
        assert response.json()["facts"][0]["value"] == "15000.00"
        svg = client.post("/v1/chart.svg", json={"question": "青禾科技2023至2025年收入画图"})
        assert svg.status_code == 200 and svg.headers["content-type"].startswith("image/svg+xml")
        assert "15000.00" in svg.text


@pytest.mark.parametrize(
    "payload",
    [{"question": ""}, {"question": "x" * 501}, {"question": "净利率", "sql": "DROP TABLE"}],
)
def test_invalid_request_is_422(copilot, payload):
    with TestClient(create_app(copilot=copilot)) as client:
        assert client.post("/v1/ask", json=payload).status_code == 422


def test_capacity_is_429_and_restored(copilot):
    app = create_app(copilot=copilot)
    with TestClient(app) as client:
        for _ in range(4):
            app.state.capacity.acquire()
        response = client.post("/v1/ask", json={"question": "青禾科技2025年营业收入"})
        assert response.status_code == 429 and response.headers["Retry-After"] == "2"
        for _ in range(4):
            app.state.capacity.release()
        assert (
            client.post("/v1/ask", json={"question": "青禾科技2025年营业收入"}).status_code == 200
        )


@pytest.mark.parametrize(
    "patch",
    [
        {"companies": ["600000"]},
        {"years": [True]},
        {"years": ["2025"]},
        {"metric": "sql"},
        {"companies": ["DEMO_A", "DEMO_A"]},
    ],
)
def test_model_schema_rejects_unsupported_scope(patch):
    data = dict(
        intent="metric",
        companies=["DEMO_A"],
        years=[2025],
        metric="revenue",
        retrieval_query="test",
        note="",
    )
    data.update(patch)
    with pytest.raises(ValidationError):
        QueryPlan.model_validate(data)
