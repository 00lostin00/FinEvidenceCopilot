import re
from typing import Protocol

from .models import QueryPlan

ALIASES = {"DEMO_A": ["demo_a", "青禾", "青禾科技"], "DEMO_B": ["demo_b", "澄海", "澄海制造"]}


def blocked_question(question: str) -> bool:
    return bool(
        re.search(
            r"买入|卖出|加仓|减仓|荐股|目标价|保本|稳赚|保证收益|预测股价|值得买|该不该买", question
        )
    )


class Planner(Protocol):
    def plan(self, question: str) -> QueryPlan: ...


class OfflinePlanner:
    def plan(self, question: str) -> QueryPlan:
        if blocked_question(question):
            return QueryPlan(
                intent="blocked",
                companies=[],
                years=[],
                metric="revenue",
                retrieval_query=question,
                note="本原型仅提供资料与指标，不处理交易建议或收益承诺",
            )
        companies = [
            company
            for company, names in ALIASES.items()
            if any(n in question.lower() for n in names)
        ]
        years = sorted(set(int(year) for year in re.findall(r"(?<!\d)(20\d{2})(?!\d)", question)))
        year_range = re.search(r"(20\d{2})年?\s*(?:到|至|-)\s*(20\d{2})年?", question)
        invalid_range = False
        if year_range:
            first, last = map(int, year_range.groups())
            invalid_range = not 0 <= last - first <= 3
            if not invalid_range:
                years = sorted(set(years) | set(range(first, last + 1)))
        if "同比" in question:
            metric = "revenue_yoy"
        elif "净利率" in question:
            metric = "net_margin"
        elif "现金流" in question:
            metric = "operating_cashflow"
        elif "净利润" in question or "利润" in question:
            metric = "net_profit"
        else:
            metric = "revenue"
        intent = "faq"
        note = ""
        if blocked_question(question):
            intent = "blocked"
            note = "本原型仅提供资料与指标，不处理交易建议或收益承诺"
        elif "最新" in question or "实时" in question or "股价" in question:
            intent = "clarify"
            note = "固定样本没有实时行情或最新披露，请指定虚构公司与年度样本"
        elif companies:
            if not years:
                years = [2025]
                note = "未指定年度，使用2025年度虚构样本"
            intent = "chart" if any(word in question for word in ["图", "可视化"]) else "metric"
            if len(companies) == 2 and intent != "chart":
                intent = "compare"
        elif re.search(r"\b\d{6}\b", question) or any(
            word in question for word in ["公司", "科技", "制造", "同花顺", "茅台", "腾讯", "苹果"]
        ):
            intent = "clarify"
            note = "只收录青禾科技DEMO_A与澄海制造DEMO_B两家虚构公司"
        if len(years) > 4:
            intent = "clarify"
            years = []
            note = "一次最多查询4个年度"
        if invalid_range:
            intent = "clarify"
            years = []
            note = "年度范围须递增，且一次最多查询4个年度"
        explicit_years = re.findall(r"(?<!\d)(\d{4})(?!\d)", question)
        if any(not 2000 <= int(year) <= 2099 for year in explicit_years):
            intent = "clarify"
            years = []
            note = "本版只解析2000至2099的四位年度，不能替换为默认年度"
        if companies and (
            re.search(r"\b\d{6}\b", question)
            or any(name in question for name in ["同花顺", "茅台", "腾讯", "苹果"])
        ):
            intent = "clarify"
            note = "查询包含样本之外的公司，请仅指定虚构公司"
        if companies and intent in {"metric", "chart", "compare"}:
            if "同比" in question and any(
                term in question for term in ["净利润", "现金流", "净利率"]
            ):
                intent = "clarify"
                note = "本版同比仅支持营业收入，未实现该指标的同比计算"
            if any(
                term in question
                for term in [
                    "毛利",
                    "扣非",
                    "归母",
                    "总资产",
                    "营业成本",
                    "投资现金流",
                    "筹资现金流",
                    "自由现金流",
                ]
            ) or ("利润" in question and "净利润" not in question):
                intent = "clarify"
                note = "该指标口径未收录，请使用营业收入、净利润或经营现金流等已支持口径"
            if not any(
                term in question for term in ["收入", "营收", "利润", "现金流", "净利率", "同比"]
            ):
                intent = "clarify"
                note = "请指定收入、净利润、经营现金流、净利率或收入同比中的一个指标"
            if re.search(r"季度|半年|Q[1-4]", question, re.IGNORECASE):
                intent = "clarify"
                note = "样本只有年度数据，不包含季度或半年报"
            selected_metrics = sum(
                [
                    "收入" in question or "营收" in question,
                    "净利润" in question,
                    "现金流" in question,
                    "净利率" in question,
                ]
            )
            if selected_metrics > 1:
                intent = "clarify"
                note = "一次查询一个指标，请分别查询收入、净利润、现金流或净利率"
        return QueryPlan(
            intent=intent,
            companies=companies,
            years=years,
            metric=metric,
            retrieval_query=question,
            note=note,
        )
