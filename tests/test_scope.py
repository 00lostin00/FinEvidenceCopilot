import pytest


@pytest.mark.parametrize(
    "question",
    [
        "青禾科技2025年扣非净利润",
        "青禾科技2025年投资现金流",
        "青禾科技2025年利润",
        "青禾科技和同花顺2025年收入比较",
        "青禾科技2025年净利润同比",
        "青禾科技2025年经营现金流同比",
        "青禾科技1999年营业收入",
    ],
)
def test_distinct_accounting_scopes_are_not_silently_substituted(copilot, question):
    result = copilot.ask(question)
    assert result.status == "clarify" and result.facts == []


def test_generic_overlap_does_not_make_nonfinancial_question_answerable(copilot):
    assert copilot.ask("量子纠缠数据的定义是什么").status == "no_evidence"


def test_blocked_route_takes_precedence_over_invalid_range(copilot):
    assert copilot.ask("青禾科技2020至2025年可以保证收益买入吗").status == "blocked"
