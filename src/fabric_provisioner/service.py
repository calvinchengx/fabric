from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fabric_provisioner.audit import AuditSink, emit_stdout
from fabric_provisioner.auth import acquire_client_credentials_token
from fabric_provisioner.config import Settings
from fabric_provisioner.fabric_client import FabricClient
from fabric_provisioner.graph_client import GraphClient
from fabric_provisioner.ports import TicketCatalogPort


@dataclass(frozen=True)
class GroupRoleAssignment:
    object_id: str
    role: str


@dataclass(frozen=True)
class SpnRoleAssignment:
    object_id: str
    role: str


@dataclass(frozen=True)
class ProvisionWorkspaceInput:
    display_name: str
    description: str | None = None
    capacity_id: str | None = None
    domain_id: str | None = None
    group_assignments: tuple[GroupRoleAssignment, ...] = ()
    spn_assignments: tuple[SpnRoleAssignment, ...] = ()
    ticket_id: str | None = None
    correlation_id: str | None = None


def provision_workspace(
    settings: Settings,
    req: ProvisionWorkspaceInput,
    *,
    port: TicketCatalogPort,
    audit: AuditSink,
) -> dict[str, Any]:
    """
    Create a Fabric workspace and assign default Entra **group** and optional
    **service principal** workspace roles.

    The provisioner itself uses client credentials (an SPN); tenant settings must
    allow that identity to create workspaces and call Fabric APIs per Microsoft Learn.
    """
    fabric_token = acquire_client_credentials_token(
        tenant_id=settings.azure_tenant_id,
        client_id=settings.azure_client_id,
        client_secret=settings.azure_client_secret,
        scope=settings.fabric_api_scope,
    )

    if settings.validate_group_ids_with_graph and (
        req.group_assignments or req.spn_assignments
    ):
        graph_token = acquire_client_credentials_token(
            tenant_id=settings.azure_tenant_id,
            client_id=settings.azure_client_id,
            client_secret=settings.azure_client_secret,
            scope=settings.graph_api_scope,
        )
        with GraphClient(base_url=settings.graph_api_base, access_token=graph_token) as graph:
            for g in req.group_assignments:
                graph.get_group(g.object_id)
            for s in req.spn_assignments:
                graph.get_service_principal(s.object_id)

    with FabricClient(base_url=settings.fabric_api_base, access_token=fabric_token) as fabric:
        workspace = fabric.create_workspace(
            display_name=req.display_name,
            description=req.description,
            capacity_id=req.capacity_id,
            domain_id=req.domain_id,
        )
        workspace_id = str(workspace["id"])
        audit.emit(
            "workspace.created",
            workspace_id=workspace_id,
            display_name=req.display_name,
            ticket_id=req.ticket_id,
            correlation_id=req.correlation_id,
        )
        emit_stdout(
            "workspace.created",
            workspace_id=workspace_id,
            display_name=req.display_name,
            ticket_id=req.ticket_id,
            correlation_id=req.correlation_id,
        )

        for g in req.group_assignments:
            fabric.add_workspace_role_assignment(
                workspace_id=workspace_id,
                principal_id=g.object_id,
                principal_type="Group",
                role=g.role,
            )
            audit.emit(
                "workspace.group_assigned",
                workspace_id=workspace_id,
                group_object_id=g.object_id,
                role=g.role,
                ticket_id=req.ticket_id,
                correlation_id=req.correlation_id,
            )
            emit_stdout(
                "workspace.group_assigned",
                workspace_id=workspace_id,
                group_object_id=g.object_id,
                role=g.role,
                ticket_id=req.ticket_id,
                correlation_id=req.correlation_id,
            )

        for s in req.spn_assignments:
            fabric.add_workspace_role_assignment(
                workspace_id=workspace_id,
                principal_id=s.object_id,
                principal_type="ServicePrincipal",
                role=s.role,
            )
            audit.emit(
                "workspace.spn_assigned",
                workspace_id=workspace_id,
                spn_object_id=s.object_id,
                role=s.role,
                ticket_id=req.ticket_id,
                correlation_id=req.correlation_id,
            )
            emit_stdout(
                "workspace.spn_assigned",
                workspace_id=workspace_id,
                spn_object_id=s.object_id,
                role=s.role,
                ticket_id=req.ticket_id,
                correlation_id=req.correlation_id,
            )

    payload: dict[str, Any] = {
        "workspace": workspace,
        "ticket_id": req.ticket_id,
        "correlation_id": req.correlation_id,
        "group_assignments": [
            {"object_id": g.object_id, "role": g.role} for g in req.group_assignments
        ],
        "spn_assignments": [
            {"object_id": s.object_id, "role": s.role} for s in req.spn_assignments
        ],
    }
    port.notify_provisioned(payload)
    return workspace
