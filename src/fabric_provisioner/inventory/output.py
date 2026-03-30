"""Write manifest JSON to disk (optional gzip)."""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any


def write_manifest_json(
    path: Path,
    manifest: dict[str, Any],
    *,
    gzip_compress: bool,
) -> None:
    """Write UTF-8 JSON (compact). If ``gzip_compress`` is True, use gzip (.gz recommended)."""
    payload = json.dumps(manifest, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    if gzip_compress:
        with gzip.open(path, "wb") as zf:
            zf.write(payload)
    else:
        path.write_bytes(payload)
