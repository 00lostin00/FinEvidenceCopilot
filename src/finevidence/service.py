import time
import uuid
from pathlib import Path
from typing import Literal

from .finance import METRIC_NAMES, FinancialStore, MissingDataError
from .models import AskResponse, QueryPlan
from .planning import OfflinePlanner, Planner, blocked_question
from .retrieval import BM25Index
from .tracing import TraceWriter


class Copilot:
    def __init__(
        self,
        project_root: Path,
        trace_path: Path | None = None,
        provider: Literal["offline", "llm"] = "offline",
        planner: Planner | None = None,
    ):
        self.store = FinancialStore(project_root / "fixtures" / "financials.json")
        self.index = BM25Index(project_root / "fixtures" / "documents.json")
        self.trace = TraceWriter(trace_path or project_root / "data" / "traces.jsonl")
        self.provider = provider
        if planner is not None:
            self.planner = planner
        elif provider == "llm":
            from .llm import LangChainPlanner

            self.planner = LangChainPlanner()
        else:
            self.planner = OfflinePlanner()

    def ask(self, question: str) -> AskResponse:
        run_id = uuid.uuid4().hex
        start = time.perf_counter()
        self.trace.emit(run_id, "request.started", provider=self.provider, chars=len(question))
        facts = []
        evidence = []
        chart = None
        # Deterministic checks run before any remote call and supplement model planning.
        deterministic = OfflinePlanner().plan(question)
        if deterministic.intent in {"blocked", "clarify"}:
            plan = deterministic
        else:
            try:
                plan = self.planner.plan(question)
                if deterministic.intent in {"metric", "compare", "chart"} and (
                    plan.companies != deterministic.companies
                    or sorted(plan.years) != deterministic.years
                    or plan.metric != deterministic.metric
                    or plan.intent != deterministic.intent
                ):
                    raise ValueError("model plan contradicts explicit query scope")
            except Exception:
                self.trace.emit(run_id, "planner.failed")
                plan = QueryPlan(
                    intent="clarify",
                    companies=[],
                    years=[],
                    metric="revenue",
                    retrieval_query=question,
                    note="规划服务失败，请检查配置或重述问题",
                )
        if blocked_question(question):
            plan = deterministic
        self.trace.emit(run_id, "plan.completed", plan=plan.model_dump())
        if plan.intent in {"clarify", "blocked"}:
            status = plan.intent
            answer = plan.note or "请指定公司、年度和一个指标"
        elif plan.intent == "faq":
            financial_terms = [
                "利润",
                "现金流",
                "净利率",
                "同比",
                "营业收入",
                "报告期",
                "财报",
                "报表",
                "来源",
                "时效",
            ]
            if any(term in question for term in financial_terms):
                evidence = self.index.search(plan.retrieval_query, [], [])
            if evidence:
                status = "answered"
                answer = "\n\n".join(f"[{item.id}] {item.text}" for item in evidence)
            else:
                status = "no_evidence"
                answer = "本地材料未找到相关证据，请改写问题或补充资料"
        else:
            try:
                facts = [
                    self.store.metric(company, year, plan.metric)
                    for company in plan.companies
                    for year in sorted(plan.years)
                ]
                evidence = self.index.search(plan.retrieval_query, list(plan.companies), plan.years)
                answer = "\n".join(
                    f"{self.store.names[f.company]} {f.year}年 {METRIC_NAMES[f.metric]}："
                    f"{f.value}{f.unit} [{f.source}]"
                    for f in facts
                )
                if plan.note:
                    answer = plan.note + "\n" + answer
                if plan.intent == "chart":
                    chart = self.store.chart(facts)
                status = "answered"
            except MissingDataError as error:
                facts = []
                status = "no_evidence"
                answer = str(error)
        self.trace.emit(
            run_id,
            "evidence.completed",
            document_ids=[e.id for e in evidence],
            fact_sources=[fact.source for fact in facts],
        )
        elapsed = round((time.perf_counter() - start) * 1000, 3)
        self.trace.emit(run_id, "request.completed", status=status, elapsed_ms=elapsed)
        return AskResponse(
            run_id=run_id,
            status=status,
            provider=self.provider,
            plan=plan,
            answer=answer,
            facts=facts,
            evidence=evidence,
            chart=chart,
            dataset_version=self.store.version,
            elapsed_ms=elapsed,
        )
