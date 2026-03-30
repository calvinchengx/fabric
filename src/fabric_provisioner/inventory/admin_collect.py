"""Admin / Power BI Scanner–style inventory (plan Phase B — stub)."""

from __future__ import annotations

from typing import Any


def collect_admin_inventory() -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """
    Returns (admin_scan_payload, error_record).

    Phase B will call Power BI / Fabric admin APIs (separate base URL and permissions).
    Until then, (None, error) so ``inventory full`` can merge with ``core`` and record why
    ``admin_scan`` is empty.
    """
    err: dict[str, Any] = {
        "scope": "admin_scan",
        "code": "not_implemented",
        "message": (
            "Admin/scanner inventory is not implemented yet — see plan/README.md Phase B."
        ),
    }
    return None, err
