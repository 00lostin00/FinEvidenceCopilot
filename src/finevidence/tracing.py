import json
import threading
from datetime import UTC, datetime
from pathlib import Path


class TraceWriter:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()

    def emit(self, run_id: str, event: str, **payload: object) -> None:
        row = {
            "time": datetime.now(UTC).isoformat(),
            "run_id": run_id,
            "event": event,
            "payload": payload,
        }
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
