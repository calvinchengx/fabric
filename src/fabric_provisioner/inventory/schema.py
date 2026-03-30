"""Unified manifest JSON shape (v1). See ../plan/README.md."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

MANIFEST_VERSION = "1"


def build_full_manifest(
    *,
    tenant_id: str,
    core: dict[str, Any] | None = None,
    admin_scan: dict[str, Any] | None = None,
    errors: list[dict[str, Any]] | None = None,
    correlation_id: str | None = None,
    ticket_id: str | None = None,
) -> dict[str, Any]:
    """Assemble the top-level manifest document."""
    return {
        "manifest_version": MANIFEST_VERSION,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "tenant_id": tenant_id,
        "correlation_id": correlation_id,
        "ticket_id": ticket_id,
        "core": core,
        "admin_scan": admin_scan,
        "errors": list(errors or []),
    }
