from __future__ import annotations

from functools import lru_cache
from typing import cast

from fastapi import FastAPI, HTTPException

from fabric_provisioner.audit import AuditSink
from fabric_provisioner.config import Settings, load_settings
from fabric_provisioner.connections import (
    ConnectionPrincipalGrant,
    ConnectionRole,
    CreateShareableSqlConnectionInput,
    SqlBasicCredentials,
    SqlServicePrincipalCredentials,
    create_shareable_sql_connection,
)
from fabric_provisioner.models import (
    CreateSqlConnectionRequest,
    ProvisionWorkspaceRequest,
    UpdateWorkspaceRoleAssignmentRequest,
)
from fabric_provisioner.ports import NoOpTicketCatalogPort, WebhookTicketCatalogPort
from fabric_provisioner.service import (
    GroupRoleAssignment,
    ProvisionWorkspaceInput,
    SpnRoleAssignment,
    provision_workspace,
    update_workspace_role_assignment,
)

app = FastAPI(
    title="fabric-provisioner",
    description="Fabric workspace and shareable SQL connection API (client credentials).",
    version="0.1.0",
)


@lru_cache
def get_settings() -> Settings:
    return load_settings()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/workspaces")
def create_workspace(body: ProvisionWorkspaceRequest) -> dict:
    settings = get_settings()
    port: NoOpTicketCatalogPort | WebhookTicketCatalogPort
    if settings.integration_webhook_url:
        port = WebhookTicketCatalogPort(settings.integration_webhook_url)
    else:
        port = NoOpTicketCatalogPort()
    audit = AuditSink(settings.audit_jsonl_path)

    req = ProvisionWorkspaceInput(
        display_name=body.display_name,
        description=body.description,
        capacity_id=body.capacity_id,
        domain_id=body.domain_id,
        group_assignments=tuple(
            GroupRoleAssignment(object_id=g.object_id, role=g.role) for g in body.group_assignments
        ),
        spn_assignments=tuple(
            SpnRoleAssignment(object_id=s.object_id, role=s.role) for s in body.spn_assignments
        ),
        ticket_id=body.ticket_id,
        correlation_id=body.correlation_id,
    )
    try:
        return provision_workspace(settings, req, port=port, audit=audit)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(e)) from e


@app.patch("/v1/workspaces/{workspace_id}/role-assignments/{assignment_id}")
def patch_workspace_role_assignment(
    workspace_id: str,
    assignment_id: str,
    body: UpdateWorkspaceRoleAssignmentRequest,
) -> dict:
    """Update a workspace role assignment (requires admin on the workspace)."""
    settings = get_settings()
    audit = AuditSink(settings.audit_jsonl_path)
    try:
        return update_workspace_role_assignment(
            settings,
            workspace_id=workspace_id,
            workspace_role_assignment_id=assignment_id,
            role=body.role,
            audit=audit,
            ticket_id=body.ticket_id,
            correlation_id=body.correlation_id,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(e)) from e


@app.post("/v1/connections/sql")
def create_sql_connection(body: CreateSqlConnectionRequest) -> dict:
    """Create a shareable cloud SQL connection and optional User/Group/SPN connection roles."""
    settings = get_settings()
    port: NoOpTicketCatalogPort | WebhookTicketCatalogPort
    if settings.integration_webhook_url:
        port = WebhookTicketCatalogPort(settings.integration_webhook_url)
    else:
        port = NoOpTicketCatalogPort()
    audit = AuditSink(settings.audit_jsonl_path)

    if body.basic is not None:
        creds: SqlBasicCredentials | SqlServicePrincipalCredentials = SqlBasicCredentials(
            username=body.basic.username,
            password=body.basic.password,
        )
    else:
        assert body.service_principal is not None
        creds = SqlServicePrincipalCredentials(
            tenant_id=body.service_principal.tenant_id,
            client_id=body.service_principal.client_id,
            client_secret=body.service_principal.client_secret,
        )
    grants = tuple(
        ConnectionPrincipalGrant(
            object_id=g.object_id,
            principal_type=g.principal_type,
            role=cast(ConnectionRole, g.role),
        )
        for g in body.grants
    )
    req = CreateShareableSqlConnectionInput(
        display_name=body.display_name,
        server=body.server,
        database=body.database,
        credentials=creds,
        grants=grants,
        ticket_id=body.ticket_id,
        correlation_id=body.correlation_id,
        privacy_level=body.privacy_level,
        allow_usage_in_user_controlled_code=body.allow_usage_in_user_controlled_code,
        skip_test_connection=body.skip_test_connection,
    )
    try:
        return create_shareable_sql_connection(settings, req, port=port, audit=audit)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(e)) from e
