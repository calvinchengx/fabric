from __future__ import annotations

import json
import sys
from collections import deque
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.json import JSON

from fabric_provisioner.audit import AuditSink
from fabric_provisioner.auth import acquire_client_credentials_token
from fabric_provisioner.config import load_settings
from fabric_provisioner.ports import NoOpTicketCatalogPort, WebhookTicketCatalogPort
from fabric_provisioner.service import (
    GroupRoleAssignment,
    ProvisionWorkspaceInput,
    provision_workspace,
)

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()


@app.command("health")
def health() -> None:
    """Acquire a Fabric API token (validates credentials)."""
    settings = load_settings()
    acquire_client_credentials_token(
        tenant_id=settings.azure_tenant_id,
        client_id=settings.azure_client_id,
        client_secret=settings.azure_client_secret,
        scope=settings.fabric_api_scope,
    )
    console.print("[green]ok[/green] — Fabric API token acquired")


@app.command("create-workspace")
def create_workspace(
    display_name: str = typer.Argument(..., help="Workspace display name"),
    description: Annotated[str | None, typer.Option(help="Optional description")] = None,
    capacity_id: Annotated[str | None, typer.Option(help="Optional Fabric capacity UUID")] = None,
    domain_id: Annotated[str | None, typer.Option(help="Optional domain UUID")] = None,
    group_id: Annotated[
        list[str],
        typer.Option(help="Entra group object ID (repeat for multiple groups)"),
    ] = [],
    group_role: Annotated[
        str,
        typer.Option(help="Role applied to every --group-id (default Member)"),
    ] = "Member",
    ticket_id: Annotated[
        str | None,
        typer.Option(help="External ticket / catalog reference"),
    ] = None,
    correlation_id: Annotated[
        str | None,
        typer.Option(help="Correlation id for logs"),
    ] = None,
) -> None:
    """Create a workspace and optionally assign Entra groups (same role for all --group-id)."""
    allowed = {"Admin", "Member", "Contributor", "Viewer"}
    if group_role not in allowed:
        console.print(f"[red]group_role must be one of {sorted(allowed)}[/red]")
        raise typer.Exit(code=1)

    settings = load_settings()
    assignments = tuple(GroupRoleAssignment(object_id=g, role=group_role) for g in group_id)
    req = ProvisionWorkspaceInput(
        display_name=display_name,
        description=description,
        capacity_id=capacity_id,
        domain_id=domain_id,
        group_assignments=assignments,
        ticket_id=ticket_id,
        correlation_id=correlation_id,
    )
    port: NoOpTicketCatalogPort | WebhookTicketCatalogPort
    if settings.integration_webhook_url:
        port = WebhookTicketCatalogPort(settings.integration_webhook_url)
    else:
        port = NoOpTicketCatalogPort()
    audit = AuditSink(settings.audit_jsonl_path)
    try:
        workspace = provision_workspace(settings, req, port=port, audit=audit)
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1) from e
    console.print(JSON(json.dumps(workspace)))


@app.command("audit-dump")
def audit_dump(
    path: Annotated[
        Path | None,
        typer.Option(help="JSONL audit file; default: AUDIT_JSONL_PATH from settings"),
    ] = None,
    tail: Annotated[
        int | None,
        typer.Option(help="Emit only the last N lines (streaming; for large files)"),
    ] = None,
) -> None:
    """Stream provisioner audit JSONL to stdout (for agents, jq, or redirect to a file)."""
    settings = load_settings()
    resolved = path or settings.audit_jsonl_path
    if resolved is None:
        console.print("[red]Set --path or AUDIT_JSONL_PATH in the environment / .env[/red]")
        raise typer.Exit(code=1)
    if not resolved.is_file():
        console.print(f"[red]Not a file: {resolved}[/red]")
        raise typer.Exit(code=1)
    if tail is not None and tail < 1:
        console.print("[red]--tail must be >= 1[/red]")
        raise typer.Exit(code=1)

    with resolved.open(encoding="utf-8") as fh:
        if tail is None:
            for line in fh:
                sys.stdout.write(line)
        else:
            last = deque(maxlen=tail)
            for line in fh:
                last.append(line)
            sys.stdout.writelines(last)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
