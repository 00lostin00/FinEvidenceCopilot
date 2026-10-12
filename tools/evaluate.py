import json
import statistics
from pathlib import Path

from finevidence.service import Copilot

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    cases = [
        json.loads(line)
        for line in (ROOT / "evals/cases.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    copilot = Copilot(ROOT, ROOT / "data/eval-traces.jsonl")
    details = []
    latencies = []
    for case in cases:
        result = copilot.ask(case["question"])
        latencies.append(result.elapsed_ms)
        passed = result.status == case["status"] and result.plan.intent == case["intent"]
        if "values" in case:
            passed &= [fact.value for fact in result.facts] == case["values"]
        if "units" in case:
            passed &= [fact.unit for fact in result.facts] == case["units"]
        if "evidence_id" in case:
            passed &= case["evidence_id"] in [item.id for item in result.evidence]
        if "chart_points" in case:
            passed &= result.chart is not None and len(result.chart.values) == case["chart_points"]
        details.append({"id": case["id"], "passed": bool(passed), "status": result.status})
    report = {
        "scope": "offline fictional fixed regression, not LLM accuracy",
        "dataset_version": copilot.store.version,
        "cases": len(cases),
        "passed": sum(item["passed"] for item in details),
        "faq_retrieval_cases": sum("evidence_id" in case for case in cases),
        "p50_ms": round(statistics.median(latencies), 3),
        "p95_nearest_rank_ms": round(
            sorted(latencies)[max(0, -(-len(latencies) * 95 // 100) - 1)], 3
        ),
        "details": details,
    }
    output = ROOT / "docs/validation/eval-results.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["passed"] != report["cases"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
