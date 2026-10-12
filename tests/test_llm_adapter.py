import httpx

from finevidence.llm import LangChainPlanner
from finevidence.models import QueryPlan
from finevidence.service import Copilot

from .conftest import ROOT


def test_real_langchain_chain_assembles_without_network(monkeypatch):
    def fail_send(*args, **kwargs):
        raise AssertionError("no network is allowed in assembly test")

    monkeypatch.setenv("OPENAI_API_KEY", "local-test-only-not-a-real-key")
    monkeypatch.setenv("FINEVIDENCE_MODEL", "local-schema-test")
    monkeypatch.setattr(httpx.Client, "send", fail_send)
    adapter = LangChainPlanner()
    assert adapter.structured is not None


def test_adapter_revalidates_stub_output():
    class StubStructured:
        def invoke(self, messages):
            assert messages[0][0] == "system" and messages[1][0] == "human"
            return QueryPlan(
                intent="metric",
                companies=["DEMO_A"],
                years=[2025],
                metric="revenue",
                retrieval_query=messages[1][1],
                note="",
            )

    adapter = object.__new__(LangChainPlanner)
    adapter.structured = StubStructured()
    assert adapter.plan("青禾科技2025年营业收入").companies == ["DEMO_A"]


def test_provider_failure_is_visible_and_not_silently_offline(tmp_path):
    class BrokenPlanner:
        def plan(self, question):
            raise TimeoutError("test timeout")

    service = Copilot(ROOT, tmp_path / "trace.jsonl", provider="llm", planner=BrokenPlanner())
    result = service.ask("青禾科技2025年营业收入")
    assert result.provider == "llm" and result.status == "clarify"
    assert result.facts == [] and "规划服务失败" in result.answer
