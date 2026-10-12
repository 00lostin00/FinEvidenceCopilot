"""Start an isolated server, verify actual HTTP, save reviewable demo artifacts."""

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from xml.etree import ElementTree

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/validation"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    environment = os.environ.copy()
    environment["FINEVIDENCE_PROVIDER"] = "offline"
    environment["FINEVIDENCE_ROOT"] = str(ROOT)
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "finevidence.api:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=ROOT,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=10) as client:
            for _ in range(50):
                try:
                    if client.get("/health").status_code == 200:
                        break
                except httpx.ConnectError:
                    pass
                if process.poll() is not None:
                    raise RuntimeError("isolated server exited before ready")
                time.sleep(0.1)
            else:
                raise RuntimeError("isolated server startup timed out")
            question = "青禾科技2023至2025年收入画图"
            response = client.post("/v1/ask", json={"question": question})
            response.raise_for_status()
            payload = response.json()
            assert [fact["value"] for fact in payload["facts"]] == [
                "10000.00",
                "12000.00",
                "15000.00",
            ]
            (OUTPUT / "demo-response.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            svg = client.post("/v1/chart.svg", json={"question": question})
            svg.raise_for_status()
            ElementTree.fromstring(svg.text)
            (OUTPUT / "demo-revenue.svg").write_text(svg.text, encoding="utf-8")
            bad = client.post("/v1/ask", json={"question": ""})
            assert bad.status_code == 422
            missing = client.post("/v1/ask", json={"question": "青禾科技2026年收入"})
            assert missing.json()["status"] == "no_evidence"
            summary = {
                "health": "passed",
                "ask": "passed",
                "chart_svg_xml": "passed",
                "invalid_422": "passed",
                "missing_period": "passed",
                "provider": "offline",
            }
            (OUTPUT / "http-smoke.json").write_text(
                json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(json.dumps(summary, ensure_ascii=False))
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


if __name__ == "__main__":
    main()
