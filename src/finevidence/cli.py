import argparse
import os
from pathlib import Path

from .charts import render_svg
from .models import AskRequest
from .service import Copilot


def main() -> None:
    parser = argparse.ArgumentParser(description="FinEvidence fictional financial copilot")
    parser.add_argument("question")
    parser.add_argument("--provider", choices=["offline", "llm"], default="offline")
    parser.add_argument("--svg", type=Path)
    args = parser.parse_args()
    root = Path(os.getenv("FINEVIDENCE_ROOT", Path(__file__).resolve().parents[2]))
    request = AskRequest(question=args.question)
    response = Copilot(root, provider=args.provider).ask(request.question)
    print(response.model_dump_json(indent=2))
    if args.svg:
        if response.chart is None:
            parser.error("--svg requires a chart question")
        args.svg.parent.mkdir(parents=True, exist_ok=True)
        args.svg.write_text(render_svg(response.chart), encoding="utf-8")


if __name__ == "__main__":
    main()
