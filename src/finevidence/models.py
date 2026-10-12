from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Company = Literal["DEMO_A", "DEMO_B"]
Metric = Literal["revenue", "net_profit", "operating_cashflow", "net_margin", "revenue_yoy"]
Intent = Literal["faq", "metric", "compare", "chart", "clarify", "blocked"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AskRequest(StrictModel):
    question: str = Field(min_length=1, max_length=500)


class QueryPlan(StrictModel):
    intent: Intent
    companies: list[Company] = Field(max_length=2)
    years: list[Annotated[int, Field(strict=True)]] = Field(max_length=4)
    metric: Metric
    retrieval_query: str = Field(max_length=500)
    note: str = Field(max_length=250)

    @model_validator(mode="after")
    def check_scope(self) -> "QueryPlan":
        if any(type(year) is not int or not 2000 <= year <= 2100 for year in self.years):
            raise ValueError("years must be integers between 2000 and 2100")
        if len(set(self.companies)) != len(self.companies) or len(set(self.years)) != len(
            self.years
        ):
            raise ValueError("duplicate companies or years")
        if self.intent in {"metric", "compare", "chart"} and (not self.companies or not self.years):
            raise ValueError("numeric queries require company and year")
        if self.intent == "compare" and len(self.companies) != 2:
            raise ValueError("comparison requires two companies")
        return self


class Evidence(StrictModel):
    id: str
    title: str
    text: str
    source: str
    company: Company | None
    year: int | None
    score: float


class Fact(StrictModel):
    company: Company
    year: int
    metric: Metric
    value: str  # Decimal display, never JSON binary float arithmetic.
    unit: str
    source: str
    formula: str


class ChartSpec(StrictModel):
    chart_type: Literal["bar"] = "bar"
    title: str
    unit: str
    labels: list[str]
    values: list[str]
    source_refs: list[str]

    @model_validator(mode="after")
    def aligned(self) -> "ChartSpec":
        if not self.labels or not (len(self.labels) == len(self.values) == len(self.source_refs)):
            raise ValueError("chart labels, values and sources must align")
        return self


class AskResponse(StrictModel):
    run_id: str
    status: Literal["answered", "clarify", "no_evidence", "blocked"]
    provider: Literal["offline", "llm"]
    plan: QueryPlan
    answer: str
    facts: list[Fact] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    chart: ChartSpec | None = None
    dataset_version: str
    elapsed_ms: float
    disclaimer: str = "全部公司、报表及金额均为虚构教学样本，不是实时行情或投资建议。"
