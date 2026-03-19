from unittest.mock import MagicMock, patch

from fabric_provisioner.audit import AuditSink
from fabric_provisioner.config import Settings
from fabric_provisioner.ports import NoOpTicketCatalogPort
from fabric_provisioner.service import (
    GroupRoleAssignment,
    ProvisionWorkspaceInput,
    SpnRoleAssignment,
    provision_workspace,
)


def test_provision_workspace_creates_and_assigns_groups() -> None:
    settings = Settings(
        azure_tenant_id="t",
        azure_client_id="c",
        azure_client_secret="s",
        validate_group_ids_with_graph=False,
    )
    req = ProvisionWorkspaceInput(
        display_name="WS-Test",
        group_assignments=(
            GroupRoleAssignment(object_id="11111111-1111-1111-1111-111111111111", role="Member"),
        ),
        ticket_id="CHG123",
    )
    fake_fabric = MagicMock()
    fake_fabric.create_workspace.return_value = {"id": "ws-1", "displayName": "WS-Test"}
    fake_fabric.__enter__ = MagicMock(return_value=fake_fabric)
    fake_fabric.__exit__ = MagicMock(return_value=False)

    with (
        patch("fabric_provisioner.service.acquire_client_credentials_token", return_value="tok"),
        patch("fabric_provisioner.service.FabricClient", return_value=fake_fabric),
    ):
        out = provision_workspace(
            settings,
            req,
            port=NoOpTicketCatalogPort(),
            audit=AuditSink(None),
        )

    assert out["id"] == "ws-1"
    fake_fabric.create_workspace.assert_called_once()
    fake_fabric.add_workspace_role_assignment.assert_called_once_with(
        workspace_id="ws-1",
        principal_id="11111111-1111-1111-1111-111111111111",
        principal_type="Group",
        role="Member",
    )


def test_provision_workspace_assigns_spns() -> None:
    settings = Settings(
        azure_tenant_id="t",
        azure_client_id="c",
        azure_client_secret="s",
        validate_group_ids_with_graph=False,
    )
    req = ProvisionWorkspaceInput(
        display_name="WS-SPN",
        spn_assignments=(
            SpnRoleAssignment(object_id="22222222-2222-2222-2222-222222222222", role="Contributor"),
        ),
    )
    fake_fabric = MagicMock()
    fake_fabric.create_workspace.return_value = {"id": "ws-2", "displayName": "WS-SPN"}
    fake_fabric.__enter__ = MagicMock(return_value=fake_fabric)
    fake_fabric.__exit__ = MagicMock(return_value=False)

    with (
        patch("fabric_provisioner.service.acquire_client_credentials_token", return_value="tok"),
        patch("fabric_provisioner.service.FabricClient", return_value=fake_fabric),
    ):
        out = provision_workspace(
            settings,
            req,
            port=NoOpTicketCatalogPort(),
            audit=AuditSink(None),
        )

    assert out["id"] == "ws-2"
    fake_fabric.add_workspace_role_assignment.assert_called_once_with(
        workspace_id="ws-2",
        principal_id="22222222-2222-2222-2222-222222222222",
        principal_type="ServicePrincipal",
        role="Contributor",
    )
