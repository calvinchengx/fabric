import pytest
from pydantic import ValidationError

from fabric_provisioner.models import (
    ConnectionGrantSpec,
    CreateSqlConnectionRequest,
    GroupRoleSpec,
    ServicePrincipalRoleSpec,
    SqlBasicCredentialBody,
    SqlServicePrincipalCredentialBody,
    UpdateWorkspaceRoleAssignmentRequest,
)


def test_group_role_spec_accepts_member() -> None:
    g = GroupRoleSpec(object_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", role="Member")
    assert g.role == "Member"


def test_group_role_spec_rejects_invalid_role() -> None:
    with pytest.raises(ValidationError):
        GroupRoleSpec(object_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", role="Owner")


def test_spn_role_spec_accepts_viewer() -> None:
    s = ServicePrincipalRoleSpec(
        object_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", role="Viewer"
    )
    assert s.role == "Viewer"


def test_spn_role_spec_rejects_invalid_role() -> None:
    with pytest.raises(ValidationError):
        ServicePrincipalRoleSpec(
            object_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", role="Owner"
        )


def test_create_sql_connection_requires_one_credential_kind() -> None:
    with pytest.raises(ValidationError):
        CreateSqlConnectionRequest(
            display_name="x",
            server="s",
            database="d",
        )
    with pytest.raises(ValidationError):
        CreateSqlConnectionRequest(
            display_name="x",
            server="s",
            database="d",
            basic=SqlBasicCredentialBody(username="u", password="p"),
            service_principal=SqlServicePrincipalCredentialBody(
                tenant_id="t",
                client_id="c",
                client_secret="s",
            ),
        )


def test_update_workspace_role_request_accepts_contributor() -> None:
    m = UpdateWorkspaceRoleAssignmentRequest(role="Contributor")
    assert m.role == "Contributor"
    assert m.ticket_id is None


def test_update_workspace_role_request_rejects_invalid_role() -> None:
    with pytest.raises(ValidationError):
        UpdateWorkspaceRoleAssignmentRequest(role="Owner")


def test_create_sql_connection_accepts_basic_and_grants() -> None:
    m = CreateSqlConnectionRequest(
        display_name="x",
        server="srv",
        database="db",
        basic=SqlBasicCredentialBody(username="u", password="p"),
        grants=[
            ConnectionGrantSpec(
                object_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                principal_type="User",
                role="Owner",
            )
        ],
    )
    assert m.basic is not None
    assert len(m.grants) == 1
