from __future__ import annotations

import json
import os
import sys
from collections import deque
from pathlib import Path
from typing import Annotated, cast

import typer
from rich.console import Console
from rich.json import JSON

from fabric_provisioner.audit import AuditSink
from fabric_provisioner.auth import acquire_client_credentials_token
from fabric_provisioner.config import load_settings
from fabric_provisioner.connections import (
    ConnectionPrincipalGrant,
    ConnectionRole,
    CreateShareableSqlConnectionInput,
    SqlBasicCredentials,
    SqlServicePrincipalCredentials,
    create_shareable_sql_connection,
)
from fabric_provisioner.ports import NoOpTicketCatalogPort, WebhookTicketCatalogPort
from fabric_provisioner.service import (
    GroupRoleAssignment,
    ProvisionWorkspaceInput,
    SpnRoleAssignment,
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
    spn_id: Annotated[
        list[str],
        typer.Option(help="Entra service principal object ID (repeat for multiple SPNs)"),
    ] = [],
    spn_role: Annotated[
        str,
        typer.Option(help="Role applied to every --spn-id (default Member)"),
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
    if spn_role not in allowed:
        console.print(f"[red]spn_role must be one of {sorted(allowed)}[/red]")
        raise typer.Exit(code=1)

    settings = load_settings()
    group_assignments = tuple(
        GroupRoleAssignment(object_id=g, role=group_role) for g in group_id
    )
    spn_assignments = tuple(SpnRoleAssignment(object_id=s, role=spn_role) for s in spn_id)
    req = ProvisionWorkspaceInput(
        display_name=display_name,
        description=description,
        capacity_id=capacity_id,
        domain_id=domain_id,
        group_assignments=group_assignments,
        spn_assignments=spn_assignments,
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


@app.command("create-sql-connection")
def create_sql_connection(
    server: Annotated[str, typer.Option(help="SQL server host (warehouse / Azure SQL)")],
    database: Annotated[str, typer.Option(help="Database / warehouse name")],
    sql_username: Annotated[
        str | None,
        typer.Option(help="SQL login user (use with password; mutually exclusive with SPN auth)"),
    ] = None,
    sql_password: Annotated[
        str | None,
        typer.Option(
            help="SQL login password; or set FABRIC_SQL_CONNECTION_PASSWORD",
            envvar="FABRIC_SQL_CONNECTION_PASSWORD",
        ),
    ] = None,
    sql_auth_tenant_id: Annotated[
        str | None,
        typer.Option(help="Entra tenant for SQL AAD auth (mutually exclusive with --sql-username)"),
    ] = None,
    sql_auth_client_id: Annotated[
        str | None,
        typer.Option(help="App (client) id used to authenticate to SQL"),
    ] = None,
    sql_auth_client_secret: Annotated[
        str | None,
        typer.Option(
            help="Client secret for SQL AAD auth; or set FABRIC_SQL_AUTH_CLIENT_SECRET",
            envvar="FABRIC_SQL_AUTH_CLIENT_SECRET",
        ),
    ] = None,
    grant_user_id: Annotated[
        list[str],
        typer.Option(help="Entra user object id (repeat); role: --grant-user-role"),
    ] = [],
    grant_user_role: Annotated[
        str,
        typer.Option(help="Fabric connection role for every --grant-user-id"),
    ] = "User",
    grant_group_id: Annotated[
        list[str],
        typer.Option(help="Entra group object id (repeatable)"),
    ] = [],
    grant_group_role: Annotated[
        str,
        typer.Option(help="Fabric connection role for every --grant-group-id"),
    ] = "User",
    grant_spn_id: Annotated[
        list[str],
        typer.Option(help="Entra service principal object id (repeatable)"),
    ] = [],
    grant_spn_role: Annotated[
        str,
        typer.Option(help="Fabric connection role for every --grant-spn-id"),
    ] = "User",
    ticket_id: Annotated[
        str | None,
        typer.Option(help="External ticket / catalog reference"),
    ] = None,
    correlation_id: Annotated[
        str | None,
        typer.Option(help="Correlation id for logs"),
    ] = None,
    skip_test_connection: Annotated[
        bool,
        typer.Option(help="If set, skip Fabric test-connection during create"),
    ] = False,
    display_name: str = typer.Argument(..., help="Connection display name in Fabric"),
) -> None:
    """Create a Fabric shareable SQL connection; optional user/group/SPN connection roles."""
    conn_roles = {"Owner", "UserWithReshare", "User"}
    for label, r in (
        ("grant_user_role", grant_user_role),
        ("grant_group_role", grant_group_role),
        ("grant_spn_role", grant_spn_role),
    ):
        if r not in conn_roles:
            console.print(f"[red]{label} must be one of {sorted(conn_roles)}[/red]")
            raise typer.Exit(code=1)

    has_basic = sql_username is not None
    has_spn_auth = sql_auth_tenant_id is not None
    if has_basic and has_spn_auth:
        console.print(
            "[red]Use SQL basic (--sql-username) or AAD SPN (--sql-auth-*), not both[/red]"
        )
        raise typer.Exit(code=1)
    if not has_basic and not has_spn_auth:
        console.print(
            "[red]Provide --sql-username/--sql-password or full --sql-auth-* for SQL[/red]"
        )
        raise typer.Exit(code=1)

    if has_basic:
        password = sql_password or os.environ.get("FABRIC_SQL_CONNECTION_PASSWORD")
        if not password:
            console.print(
                "[red]Missing SQL password (flag or FABRIC_SQL_CONNECTION_PASSWORD)[/red]"
            )
            raise typer.Exit(code=1)
        creds: SqlBasicCredentials | SqlServicePrincipalCredentials = SqlBasicCredentials(
            username=sql_username,
            password=password,
        )
    else:
        secret = sql_auth_client_secret or os.environ.get("FABRIC_SQL_AUTH_CLIENT_SECRET")
        if not sql_auth_client_id or not secret:
            console.print(
                "[red]SQL AAD auth needs --sql-auth-client-id and client secret[/red]"
            )
            raise typer.Exit(code=1)
        assert sql_auth_tenant_id is not None
        creds = SqlServicePrincipalCredentials(
            tenant_id=sql_auth_tenant_id,
            client_id=sql_auth_client_id,
            client_secret=secret,
        )

    grants_list: list[ConnectionPrincipalGrant] = []
    for uid in grant_user_id:
        grants_list.append(
            ConnectionPrincipalGrant(
                object_id=uid,
                principal_type="User",
                role=cast(ConnectionRole, grant_user_role),
            )
        )
    for gid in grant_group_id:
        grants_list.append(
            ConnectionPrincipalGrant(
                object_id=gid,
                principal_type="Group",
                role=cast(ConnectionRole, grant_group_role),
            )
        )
    for sid in grant_spn_id:
        grants_list.append(
            ConnectionPrincipalGrant(
                object_id=sid,
                principal_type="ServicePrincipal",
                role=cast(ConnectionRole, grant_spn_role),
            )
        )

    settings = load_settings()
    req = CreateShareableSqlConnectionInput(
        display_name=display_name,
        server=server,
        database=database,
        credentials=creds,
        grants=tuple(grants_list),
        ticket_id=ticket_id,
        correlation_id=correlation_id,
        skip_test_connection=skip_test_connection,
    )
    port: NoOpTicketCatalogPort | WebhookTicketCatalogPort
    if settings.integration_webhook_url:
        port = WebhookTicketCatalogPort(settings.integration_webhook_url)
    else:
        port = NoOpTicketCatalogPort()
    audit = AuditSink(settings.audit_jsonl_path)
    try:
        connection = create_shareable_sql_connection(settings, req, port=port, audit=audit)
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1) from e
    console.print(JSON(json.dumps(connection)))


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
