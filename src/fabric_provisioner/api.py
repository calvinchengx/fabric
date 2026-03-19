from __future__ import annotations

from functools import lru_cache

from fastapi import FastAPI, HTTPException

from fabric_provisioner.audit import AuditSink
from fabric_provisioner.config import Settings, load_settings
from fabric_provisioner.models import ProvisionWorkspaceRequest
from fabric_provisioner.ports import NoOpTicketCatalogPort, WebhookTicketCatalogPort
from fabric_provisioner.service import (
    GroupRoleAssignment,
    ProvisionWorkspaceInput,
    SpnRoleAssignment,
    provision_workspace,
)

app = FastAPI(
    title="fabric-provisioner",
    description="Thin Fabric workspace provisioning API (client credentials).",
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
