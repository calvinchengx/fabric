from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


@dataclass
class AuditSink:
    """Append-only JSONL audit log; no-op if path is None."""

    path: Path | None

    def emit(self, event: str, **fields: Any) -> None:
        record = {"ts": _now_iso(), "event": event, **fields}
        if self.path is None:
            return
        line = json.dumps(record, separators=(",", ":"), sort_keys=True)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")


def emit_stdout(event: str, stream: TextIO | None = None, **fields: Any) -> None:
    """Structured one-line JSON to stdout (useful for container log aggregation)."""

    import sys

    out = stream or sys.stdout
    record = {"ts": _now_iso(), "event": event, **fields}
    out.write(json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n")
