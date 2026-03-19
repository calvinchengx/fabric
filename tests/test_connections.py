from unittest.mock import MagicMock, patch

from fabric_provisioner.audit import AuditSink
from fabric_provisioner.config import Settings
from fabric_provisioner.connections import (
    ConnectionPrincipalGrant,
    CreateShareableSqlConnectionInput,
    SqlBasicCredentials,
    build_shareable_sql_connection_payload,
    create_shareable_sql_connection,
)
from fabric_provisioner.ports import NoOpTicketCatalogPort


def test_build_payload_basic() -> None:
    inp = CreateShareableSqlConnectionInput(
        display_name="DW-Conn",
        server="x.datawarehouse.pbidedicated.windows.net",
        database="mywh",
        credentials=SqlBasicCredentials(username="u", password="p"),
        skip_test_connection=True,
    )
    body = build_shareable_sql_connection_payload(inp)
    assert body["connectivityType"] == "ShareableCloud"
    assert body["displayName"] == "DW-Conn"
    assert body["connectionDetails"]["parameters"][0]["name"] == "server"
    assert body["credentialDetails"]["credentials"]["credentialType"] == "Basic"


def test_create_sql_connection_and_grants() -> None:
    settings = Settings(
        azure_tenant_id="t",
        azure_client_id="c",
        azure_client_secret="s",
        validate_group_ids_with_graph=False,
    )
    inp = CreateShareableSqlConnectionInput(
        display_name="C1",
        server="srv",
        database="db",
        credentials=SqlBasicCredentials(username="u", password="p"),
        grants=(
            ConnectionPrincipalGrant(
                object_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                principal_type="Group",
                role="User",
            ),
            ConnectionPrincipalGrant(
                object_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                principal_type="ServicePrincipal",
                role="UserWithReshare",
            ),
        ),
        skip_test_connection=True,
    )
    fake = MagicMock()
    fake.create_connection.return_value = {"id": "conn-1", "displayName": "C1"}
    fake.add_connection_role_assignment.return_value = {"id": "ra-1"}
    fake.__enter__ = MagicMock(return_value=fake)
    fake.__exit__ = MagicMock(return_value=False)

    tok_patch = patch(
        "fabric_provisioner.connections.acquire_client_credentials_token",
        return_value="tok",
    )
    client_patch = patch(
        "fabric_provisioner.connections.FabricClient",
        return_value=fake,
    )
    with tok_patch, client_patch:
        out = create_shareable_sql_connection(
            settings,
            inp,
            port=NoOpTicketCatalogPort(),
            audit=AuditSink(None),
        )

    assert out["id"] == "conn-1"
    fake.create_connection.assert_called_once()
    assert fake.add_connection_role_assignment.call_count == 2
    first_kw = fake.add_connection_role_assignment.call_args_list[0].kwargs
    assert first_kw["connection_id"] == "conn-1"
    assert first_kw["principal"]["type"] == "Group"
    assert first_kw["principal"]["groupDetails"]["groupType"] == "SecurityGroup"
    assert first_kw["role"] == "User"
