from html.parser import HTMLParser
from xml.etree import ElementTree

import pytest
from fastapi.testclient import TestClient

from finevidence.api import create_app


class ExampleQuestions(HTMLParser):
    def __init__(self):
        super().__init__()
        self.questions = []

    def handle_starttag(self, tag, attrs):
        if tag == "button":
            question = dict(attrs).get("data-question")
            if question:
                self.questions.append(question)


def test_workbench_assets_are_served_with_browser_security_headers(copilot):
    with TestClient(create_app(copilot=copilot)) as client:
        home = client.get("/")
        assert home.status_code == 200
        assert 'lang="zh-CN"' in home.text
        assert "虚构教学样本" in home.text
        assert home.headers["cache-control"] == "no-cache"
        policy = home.headers["content-security-policy"]
        assert "script-src 'self'" in policy and "unsafe-inline" not in policy
        assert "object-src 'none'" in policy
        for path, content_type in [
            ("/static/app.css", "text/css"),
            ("/static/app.js", "javascript"),
            ("/static/logo.svg", "image/svg+xml"),
        ]:
            asset = client.get(path)
            assert asset.status_code == 200
            assert content_type in asset.headers["content-type"]
            assert asset.headers["x-content-type-options"] == "nosniff"


def test_visible_example_questions_match_live_api_capabilities(copilot):
    with TestClient(create_app(copilot=copilot)) as client:
        parser = ExampleQuestions()
        parser.feed(client.get("/").text)
        assert len(parser.questions) >= 4
        intents = set()
        for question in parser.questions:
            response = client.post("/v1/ask", json={"question": question})
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "answered", question
            intents.add(result["plan"]["intent"])
            if result["chart"]:
                chart = client.post("/v1/chart.svg", json={"question": question})
                assert chart.status_code == 200
                root = ElementTree.fromstring(chart.text)
                assert root.tag == "{http://www.w3.org/2000/svg}svg"
                assert all(value in chart.text for value in result["chart"]["values"])
        assert {"chart", "compare", "metric", "faq"}.issubset(intents)


def test_catalog_reflects_loaded_data_instead_of_fixed_frontend_counts(copilot):
    del copilot.store.rows[("DEMO_A", 2023)]
    del copilot.store.rows[("DEMO_B", 2023)]
    with TestClient(create_app(copilot=copilot)) as client:
        result = client.get("/v1/catalog").json()
        assert result["fictional"] is True
        assert result["years"] == [2024, 2025]
        assert result["record_count"] == 4
        assert result["dataset_version"] == copilot.store.version
        assert result["chunk_count"] == len(copilot.index.chunks)
        assert {item["id"] for item in result["companies"]} == {"DEMO_A", "DEMO_B"}
        assert {item["id"] for item in result["metrics"]} == {
            "revenue", "net_profit", "operating_cashflow", "net_margin", "revenue_yoy"
        }
        assert all(item["source"].startswith("fixture:") for item in result["documents"])


@pytest.mark.parametrize(
    "path",
    [
        "/static/%2e%2e/api.py",
        "/static/%2e%2e/%2e%2e/%2e%2e/fixtures/financials.json",
        "/static/.env",
        "/static/not-found.js",
    ],
)
def test_static_files_cannot_expose_source_or_unlisted_files(copilot, path):
    with TestClient(create_app(copilot=copilot)) as client:
        assert client.get(path).status_code == 404


def test_workbench_clarification_has_no_numeric_or_chart_output(copilot):
    with TestClient(create_app(copilot=copilot)) as client:
        result = client.post("/v1/ask", json={"question": "青禾科技最新收入"}).json()
        assert result["status"] == "clarify"
        assert result["facts"] == [] and result["chart"] is None
        assert "实时" in result["answer"]
