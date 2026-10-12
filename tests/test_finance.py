import pytest

from finevidence.finance import MissingDataError


@pytest.mark.parametrize(
    "company,year,metric,value,unit",
    [
        ("DEMO_A", 2025, "revenue", "15000.00", "万元"),
        ("DEMO_A", 2025, "net_margin", "10.00", "%"),
        ("DEMO_A", 2025, "revenue_yoy", "25.00", "%"),
        ("DEMO_B", 2025, "net_margin", "4.00", "%"),
        ("DEMO_B", 2025, "revenue_yoy", "5.00", "%"),
        ("DEMO_A", 2024, "operating_cashflow", "1350.00", "万元"),
    ],
)
def test_reference_arithmetic(copilot, company, year, metric, value, unit):
    result = copilot.store.metric(company, year, metric)
    assert (result.value, result.unit) == (value, unit)


def test_yoy_records_both_sources(copilot):
    assert copilot.store.metric("DEMO_A", 2025, "revenue_yoy").source == (
        "fixture:DEMO_A:2025;fixture:DEMO_A:2024"
    )


@pytest.mark.parametrize("metric,year", [("revenue", 2026), ("revenue_yoy", 2023)])
def test_missing_period_is_not_zero(copilot, metric, year):
    with pytest.raises(MissingDataError):
        copilot.store.metric("DEMO_A", year, metric)


@pytest.mark.parametrize("baseline", ["0", "-100"])
def test_nonpositive_baseline_rejected(copilot, baseline):
    copilot.store.rows[("DEMO_A", 2024)]["revenue"] = baseline
    with pytest.raises(MissingDataError):
        copilot.store.metric("DEMO_A", 2025, "revenue_yoy")


def test_zero_revenue_margin_rejected(copilot):
    copilot.store.rows[("DEMO_A", 2025)]["revenue"] = "0"
    with pytest.raises(MissingDataError):
        copilot.store.metric("DEMO_A", 2025, "net_margin")


def test_loss_produces_negative_margin(copilot):
    copilot.store.rows[("DEMO_A", 2025)]["net_profit"] = "-1500"
    assert copilot.store.metric("DEMO_A", 2025, "net_margin").value == "-10.00"
