import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from .models import ChartSpec, Company, Fact, Metric

METRIC_NAMES = {
    "revenue": "营业收入",
    "net_profit": "净利润",
    "operating_cashflow": "经营活动现金流量净额",
    "net_margin": "净利率",
    "revenue_yoy": "营业收入同比",
}


class MissingDataError(ValueError):
    pass


class FinancialStore:
    def __init__(self, fixture_path: Path):
        dataset = json.loads(fixture_path.read_text(encoding="utf-8"))
        self.version = dataset["version"]
        self.unit = dataset["unit"]
        self.names = dataset["companies"]
        self.rows = {(row["company"], row["year"]): row for row in dataset["rows"]}

    def metric(self, company: Company, year: int, metric: Metric) -> Fact:
        row = self.rows.get((company, year))
        if row is None:
            raise MissingDataError(f"样本中没有 {company} 的 {year} 年数据")
        source = row["source"]
        formula = "直接读取年度虚构样本"
        unit = self.unit
        if metric == "net_margin":
            revenue = Decimal(row["revenue"])
            if revenue <= 0:
                raise MissingDataError("营业收入不为正，无法计算本项目简化净利率")
            value = Decimal(row["net_profit"]) / revenue * 100
            unit = "%"
            formula = "净利润 / 营业收入 * 100"
        elif metric == "revenue_yoy":
            previous = self.rows.get((company, year - 1))
            if previous is None or Decimal(previous["revenue"]) <= 0:
                raise MissingDataError("缺少正值上年营业收入，无法计算同比")
            baseline = Decimal(previous["revenue"])
            value = (Decimal(row["revenue"]) - baseline) / baseline * 100
            source += ";" + previous["source"]
            unit = "%"
            formula = "(本年营业收入 - 上年营业收入) / 上年营业收入 * 100"
        else:
            value = Decimal(row[metric])
        return Fact(
            company=company,
            year=year,
            metric=metric,
            value=str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            unit=unit,
            source=source,
            formula=formula,
        )

    def chart(self, facts: list[Fact]) -> ChartSpec:
        if not facts or len({(fact.metric, fact.unit) for fact in facts}) != 1:
            raise ValueError("a chart requires one consistent metric and unit")
        return ChartSpec(
            title=f"{METRIC_NAMES[facts[0].metric]}（虚构样本）",
            unit=facts[0].unit,
            labels=[f"{self.names[fact.company]} {fact.year}" for fact in facts],
            values=[fact.value for fact in facts],
            source_refs=[fact.source for fact in facts],
        )
