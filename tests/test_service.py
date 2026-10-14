import json
from dataclasses import dataclass
from xml.etree import ElementTree

import pytest

from finevidence.charts import render_svg
from finevidence.models import ChartSpec, QueryPlan
from finevidence.service import Copilot

from .conftest import ROOT


@pytest.mark.parametrize(
    "question,status,intent",
    [
        ("青禾科技2025年营业收入", "answered", "metric"),
        ("比较青禾科技和澄海制造2025年净利率", "answered", "compare"),
        ("青禾科技2023至2025年收入画图", "answered", "chart"),
        ("青禾科技2026年净利润", "no_evidence", "metric"),
        ("青禾科技2023年营业收入同比", "no_evidence", "metric"),
        ("同花顺2025年净利润", "clarify", "clarify"),
        ("青禾科技最新股价", "clarify", "clarify"),
        ("青禾科技值得买入吗", "blocked", "blocked"),
        ("利润为什么和现金流不同", "answered", "faq"),
        ("量子纠缠的定义", "no_evidence", "faq"),
        ("青禾科技2025年收入和净利润", "clarify", "clarify"),
        ("青禾科技2025年第一季度营收", "clarify", "clarify"),
        ("青禾科技2020至2025年收入画图", "clarify", "clarify"),
        ("青禾科技2025年总资产", "clarify", "clarify"),
    ],
)
def test_business_routes(copilot, question, status, intent):
    result = copilot.ask(question)
    assert (result.status, result.plan.intent) == (status, intent)
    if status != "answered":
        assert result.facts == [] and result.chart is None


def test_scope_filtered_evidence(copilot):
    result = copilot.ask("青禾科技2025年净利润")
    assert result.evidence
    assert all(item.company == "DEMO_A" and item.year == 2025 for item in result.evidence)


def test_default_year_disclosed(copilot):
    result = copilot.ask("青禾科技营业收入")
    assert result.facts[0].year == 2025
    assert "未指定年度" in result.answer


def test_partial_missing_comparison_returns_no_facts(copilot):
    del copilot.store.rows[("DEMO_B", 2025)]
    result = copilot.ask("比较青禾科技和澄海制造2025年净利润")
    assert result.status == "no_evidence" and result.facts == []


def test_svg_contains_no_unescaped_markup():
    spec = ChartSpec(
        title="<script>alert(1)</script>",
        unit="万元",
        labels=['<img src="x">'],
        values=["-3.00"],
        source_refs=["fixture:test"],
    )
    result = render_svg(spec)
    assert "<script>" not in result and "<img" not in result
    assert "&lt;script&gt;" in result
    root = ElementTree.fromstring(result)
    axis = root.find(".//{http://www.w3.org/2000/svg}line")
    negative_bar = root.findall(".//{http://www.w3.org/2000/svg}rect")[-1]
    assert float(negative_bar.attrib["x"]) < float(axis.attrib["x1"])
    assert float(negative_bar.attrib["x"]) + float(negative_bar.attrib["width"]) == float(
        axis.attrib["x1"]
    )


def test_trace_groups_events_and_retains_plan_query(copilot):
    result = copilot.ask("青禾科技2025年净利率")
    rows = [
        json.loads(line) for line in copilot.trace.path.read_text(encoding="utf-8").splitlines()
    ]
    assert all(row["run_id"] == result.run_id for row in rows)
    assert [row["event"] for row in rows] == [
        "request.started",
        "plan.completed",
        "evidence.completed",
        "request.completed",
    ]
    # retrieval_query is retained in plan events; keys are never part of the trace schema.
    assert "OPENAI_API_KEY" not in copilot.trace.path.read_text(encoding="utf-8")


@dataclass
class FakePlanner:
    calls: int = 0

    def plan(self, question):
        self.calls += 1
        return QueryPlan(
            intent="metric",
            companies=["DEMO_B"],
            years=[2024],
            metric="revenue",
            retrieval_query=question,
            note="",
        )


def test_model_cannot_replace_explicit_company(tmp_path):
    planner = FakePlanner()
    service = Copilot(ROOT, tmp_path / "trace.jsonl", provider="llm", planner=planner)
    assert service.ask("青禾科技2025年营业收入").status == "clarify"
    assert planner.calls == 1


def test_blocked_route_skips_model(tmp_path):
    planner = FakePlanner()
    service = Copilot(ROOT, tmp_path / "trace.jsonl", provider="llm", planner=planner)
    assert service.ask("青禾科技该不该买").status == "blocked"
    assert planner.calls == 0
