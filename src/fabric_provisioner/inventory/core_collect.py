"""Fabric Core REST inventory: workspaces, items, role assignments (paginated)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from fabric_provisioner.audit import AuditSink, emit_stdout
from fabric_provisioner.auth import acquire_client_credentials_token
from fabric_provisioner.config import Settings
from fabric_provisioner.fabric_client import FabricClient


class InventoryDisabledError(Exception):
    """Raised when ``FABRIC_INVENTORY_ENABLED`` is false."""

_FABRIC_LIST_WORKSPACES = (
    "https://learn.microsoft.com/en-us/rest/api/fabric/core/workspaces/list-workspaces"
)
_FABRIC_LIST_ITEMS = (
    "https://learn.microsoft.com/en-us/rest/api/fabric/core/items/list-items"
)
_FABRIC_LIST_ROLE_ASSIGNMENTS = (
    "https://learn.microsoft.com/en-us/rest/api/fabric/core/workspaces/"
    "list-workspace-role-assignments"
)


def _collect_all_pages(
    fetch_page: Any,
    *,
    value_key: str = "value",
    token_key: str = "continuationToken",
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    token: str | None = None
    while True:
        page = fetch_page(token)
        out.extend(page.get(value_key) or [])
        token = page.get(token_key)
        if not token:
            break
    return out


@dataclass
class CoreInventoryOptions:
    """Filters and depth for Core inventory. All optional: defaults include full crawl."""

    include_items: bool = True
    include_role_assignments: bool = True
    workspace_ids: frozenset[str] | None = None
    name_prefix: str | None = None
    capacity_id: str | None = None
    domain_id: str | None = None
    max_workspaces: int | None = None
    roles: str | None = None
    prefer_workspace_specific_endpoints: bool = False
    item_recursive: bool = True


def _apply_inventory_guards(
    settings: Settings,
    options: CoreInventoryOptions | None,
) -> CoreInventoryOptions:
    """Enforce global inventory feature flag and optional workspace allowlist."""
    if not settings.inventory_enabled:
        msg = "Fabric inventory is disabled; set FABRIC_INVENTORY_ENABLED=true to enable."
        raise InventoryDisabledError(msg)
    opt = options or CoreInventoryOptions()
    allow = settings.parsed_inventory_workspace_allowlist()
    if not allow:
        return opt
    if opt.workspace_ids is None:
        return replace(opt, workspace_ids=allow)
    inter = opt.workspace_ids & allow
    if not inter:
        msg = (
            "No workspace IDs match FABRIC_INVENTORY_WORKSPACE_ALLOWLIST "
            f"(requested {sorted(opt.workspace_ids)!r})."
        )
        raise ValueError(msg)
    return replace(opt, workspace_ids=inter)


def _workspace_matches_filters(ws: dict[str, Any], opt: CoreInventoryOptions) -> bool:
    wid = str(ws.get("id", ""))
    if opt.workspace_ids is not None and wid not in opt.workspace_ids:
        return False
    display = str(ws.get("displayName") or "")
    if opt.name_prefix and not display.startswith(opt.name_prefix):
        return False
    cap = ws.get("capacityId")
    if opt.capacity_id and str(cap or "") != opt.capacity_id:
        return False
    dom = ws.get("domainId")
    if opt.domain_id and str(dom or "") != opt.domain_id:
        return False
    return True


def collect_core_inventory(
    settings: Settings,
    fabric: FabricClient,
    *,
    options: CoreInventoryOptions | None = None,
    audit: AuditSink | None = None,
    ticket_id: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """
    Build the ``core`` section for manifest v1 using an authenticated ``FabricClient``.

    Microsoft docs: list workspaces / items / role assignments require
    ``Workspace.Read.All`` or ``Workspace.ReadWrite.All`` (delegated); map to application
    permissions for client credentials per your tenant.
    """
    opt = options or CoreInventoryOptions()
    if audit:
        audit.emit(
            "inventory.core.started",
            ticket_id=ticket_id,
            correlation_id=correlation_id,
            include_items=opt.include_items,
            include_role_assignments=opt.include_role_assignments,
        )
    emit_stdout(
        "inventory.core.started",
        ticket_id=ticket_id,
        correlation_id=correlation_id,
    )

    errors: list[dict[str, Any]] = []
    workspace_summaries: list[dict[str, Any]] = []
    token: str | None = None
    done = False
    while not done:
        page = fabric.list_workspaces_page(
            continuation_token=token,
            roles=opt.roles,
            prefer_workspace_specific_endpoints=opt.prefer_workspace_specific_endpoints,
        )
        for ws in page.get("value") or []:
            if not isinstance(ws, dict):
                continue
            if not _workspace_matches_filters(ws, opt):
                continue
            workspace_summaries.append(ws)
            if opt.max_workspaces is not None and len(workspace_summaries) >= opt.max_workspaces:
                done = True
                break
        if done:
            break
        token = page.get("continuationToken")
        if not token:
            break

    entries: list[dict[str, Any]] = []
    item_total = 0
    role_total = 0

    for ws in workspace_summaries:
        wid = str(ws.get("id", ""))
        entry: dict[str, Any] = {"workspace": ws}
        if opt.include_items:
            try:
                items = _collect_all_pages(
                    lambda t: fabric.list_workspace_items_page(
                        wid,
                        continuation_token=t,
                        recursive=opt.item_recursive,
                    ),
                )
                entry["items"] = items
                item_total += len(items)
            except Exception as e:  # noqa: BLE001
                errors.append(
                    {
                        "scope": "items",
                        "workspace_id": wid,
                        "message": str(e),
                    },
                )
                entry["items"] = []
        if opt.include_role_assignments:
            try:
                roles_list = _collect_all_pages(
                    lambda t: fabric.list_workspace_role_assignments_page(
                        wid,
                        continuation_token=t,
                    ),
                )
                entry["role_assignments"] = roles_list
                role_total += len(roles_list)
            except Exception as e:  # noqa: BLE001
                errors.append(
                    {
                        "scope": "role_assignments",
                        "workspace_id": wid,
                        "message": str(e),
                    },
                )
                entry["role_assignments"] = []
        entries.append(entry)

    core: dict[str, Any] = {
        "source": "fabric_core",
        "documentation": {
            "list_workspaces": _FABRIC_LIST_WORKSPACES,
            "list_items": _FABRIC_LIST_ITEMS,
            "list_role_assignments": _FABRIC_LIST_ROLE_ASSIGNMENTS,
        },
        "api_base": settings.fabric_api_base,
        "workspaces": entries,
        "summary": {
            "workspace_count": len(entries),
            "item_count": item_total,
            "role_assignment_count": role_total,
        },
        "partial_errors": errors,
    }
    if audit:
        audit.emit(
            "inventory.core.completed",
            workspace_count=len(entries),
            item_count=item_total,
            role_assignment_count=role_total,
            error_count=len(errors),
            ticket_id=ticket_id,
            correlation_id=correlation_id,
        )
    emit_stdout(
        "inventory.core.completed",
        workspace_count=len(entries),
        item_count=item_total,
        ticket_id=ticket_id,
        correlation_id=correlation_id,
    )
    return core


def run_core_inventory_pipeline(
    settings: Settings,
    *,
    options: CoreInventoryOptions | None = None,
    audit: AuditSink | None = None,
    ticket_id: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Acquire Fabric token, open ``FabricClient``, run :func:`collect_core_inventory`."""
    options = _apply_inventory_guards(settings, options)
    fabric_token = acquire_client_credentials_token(
        tenant_id=settings.azure_tenant_id,
        client_id=settings.azure_client_id,
        client_secret=settings.azure_client_secret,
        scope=settings.fabric_api_scope,
    )
    with FabricClient(
        base_url=settings.fabric_api_base,
        access_token=fabric_token,
    ) as fabric:
        return collect_core_inventory(
            settings,
            fabric,
            options=options,
            audit=audit,
            ticket_id=ticket_id,
            correlation_id=correlation_id,
        )


def run_core_manifest_only(
    settings: Settings,
    *,
    options: CoreInventoryOptions | None = None,
    audit: AuditSink | None = None,
    ticket_id: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Full manifest v1 JSON with only the Fabric Core ``core`` section populated."""
    from fabric_provisioner.inventory.schema import build_full_manifest

    core = run_core_inventory_pipeline(
        settings,
        options=options,
        audit=audit,
        ticket_id=ticket_id,
        correlation_id=correlation_id,
    )
    return build_full_manifest(
        tenant_id=settings.azure_tenant_id,
        core=core,
        admin_scan=None,
        errors=[],
        correlation_id=correlation_id,
        ticket_id=ticket_id,
    )


def run_full_inventory_pipeline(
    settings: Settings,
    *,
    core_options: CoreInventoryOptions | None = None,
    audit: AuditSink | None = None,
    ticket_id: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Core manifest + admin stub merge via :func:`schema.build_full_manifest`."""
    from fabric_provisioner.inventory.admin_collect import collect_admin_inventory
    from fabric_provisioner.inventory.schema import build_full_manifest

    core = run_core_inventory_pipeline(
        settings,
        options=core_options,
        audit=audit,
        ticket_id=ticket_id,
        correlation_id=correlation_id,
    )
    admin_scan, admin_err = collect_admin_inventory()
    top_errors: list[dict[str, Any]] = []
    if admin_err:
        top_errors.append(admin_err)
    return build_full_manifest(
        tenant_id=settings.azure_tenant_id,
        core=core,
        admin_scan=admin_scan,
        errors=top_errors,
        correlation_id=correlation_id,
        ticket_id=ticket_id,
    )
