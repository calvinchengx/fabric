"""Fabric shareable SQL connections (warehouse / Azure SQL–style endpoints) + role grants."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from fabric_provisioner.audit import AuditSink, emit_stdout
from fabric_provisioner.auth import acquire_client_credentials_token
from fabric_provisioner.config import Settings
from fabric_provisioner.fabric_client import FabricClient
from fabric_provisioner.ports import TicketCatalogPort

ConnectionPrincipalType = Literal["User", "Group", "ServicePrincipal"]
ConnectionRole = Literal["Owner", "UserWithReshare", "User"]


@dataclass(frozen=True)
class SqlBasicCredentials:
    username: str
    password: str


@dataclass(frozen=True)
class SqlServicePrincipalCredentials:
    """Entra credentials used to authenticate the connection to SQL (not the provisioner app)."""

    tenant_id: str
    client_id: str
    client_secret: str


@dataclass(frozen=True)
class ConnectionPrincipalGrant:
    object_id: str
    principal_type: ConnectionPrincipalType
    role: ConnectionRole


@dataclass(frozen=True)
class CreateShareableSqlConnectionInput:
    display_name: str
    server: str
    database: str
    credentials: SqlBasicCredentials | SqlServicePrincipalCredentials
    grants: tuple[ConnectionPrincipalGrant, ...] = ()
    ticket_id: str | None = None
    correlation_id: str | None = None
    privacy_level: str = "Organizational"
    allow_usage_in_user_controlled_code: bool = False
    skip_test_connection: bool = False


def build_shareable_sql_connection_payload(
    inp: CreateShareableSqlConnectionInput,
) -> dict[str, Any]:
    connection_details: dict[str, Any] = {
        "type": "SQL",
        "creationMethod": "SQL",
        "parameters": [
            {"dataType": "Text", "name": "server", "value": inp.server},
            {"dataType": "Text", "name": "database", "value": inp.database},
        ],
    }
    if isinstance(inp.credentials, SqlBasicCredentials):
        cred_block: dict[str, Any] = {
            "credentialType": "Basic",
            "username": inp.credentials.username,
            "password": inp.credentials.password,
        }
    else:
        cred_block = {
            "credentialType": "ServicePrincipal",
            "tenantId": inp.credentials.tenant_id,
            "servicePrincipalClientId": inp.credentials.client_id,
            "servicePrincipalSecret": inp.credentials.client_secret,
        }
    credential_details: dict[str, Any] = {
        "singleSignOnType": "None",
        "connectionEncryption": "NotEncrypted",
        "skipTestConnection": inp.skip_test_connection,
        "credentials": cred_block,
    }
    return {
        "connectivityType": "ShareableCloud",
        "displayName": inp.display_name,
        "connectionDetails": connection_details,
        "credentialDetails": credential_details,
        "privacyLevel": inp.privacy_level,
        "allowUsageInUserControlledCode": inp.allow_usage_in_user_controlled_code,
    }


def connection_role_principal_payload(
    principal_id: str, principal_type: ConnectionPrincipalType
) -> dict[str, Any]:
    if principal_type == "Group":
        return {
            "id": principal_id,
            "type": "Group",
            "groupDetails": {"groupType": "SecurityGroup"},
        }
    return {"id": principal_id, "type": principal_type}


def create_shareable_sql_connection(
    settings: Settings,
    inp: CreateShareableSqlConnectionInput,
    *,
    port: TicketCatalogPort,
    audit: AuditSink,
) -> dict[str, Any]:
    """
    Create a Fabric shareable cloud SQL connection, then assign connection roles
    to users, groups, or service principals (Microsoft Learn: Connections API).
    """
    fabric_token = acquire_client_credentials_token(
        tenant_id=settings.azure_tenant_id,
        client_id=settings.azure_client_id,
        client_secret=settings.azure_client_secret,
        scope=settings.fabric_api_scope,
    )
    body = build_shareable_sql_connection_payload(inp)
    with FabricClient(base_url=settings.fabric_api_base, access_token=fabric_token) as fabric:
        connection = fabric.create_connection(body)
        connection_id = str(connection["id"])
        audit.emit(
            "connection.sql.created",
            connection_id=connection_id,
            display_name=inp.display_name,
            server=inp.server,
            database=inp.database,
            ticket_id=inp.ticket_id,
            correlation_id=inp.correlation_id,
        )
        emit_stdout(
            "connection.sql.created",
            connection_id=connection_id,
            display_name=inp.display_name,
            server=inp.server,
            database=inp.database,
            ticket_id=inp.ticket_id,
            correlation_id=inp.correlation_id,
        )

        for g in inp.grants:
            principal = connection_role_principal_payload(g.object_id, g.principal_type)
            fabric.add_connection_role_assignment(
                connection_id=connection_id,
                principal=principal,
                role=g.role,
            )
            audit.emit(
                "connection.role_assigned",
                connection_id=connection_id,
                principal_id=g.object_id,
                principal_type=g.principal_type,
                connection_role=g.role,
                ticket_id=inp.ticket_id,
                correlation_id=inp.correlation_id,
            )
            emit_stdout(
                "connection.role_assigned",
                connection_id=connection_id,
                principal_id=g.object_id,
                principal_type=g.principal_type,
                connection_role=g.role,
                ticket_id=inp.ticket_id,
                correlation_id=inp.correlation_id,
            )

    payload: dict[str, Any] = {
        "operation": "sql_shareable_connection",
        "connection": connection,
        "grants": [
            {
                "object_id": g.object_id,
                "principal_type": g.principal_type,
                "role": g.role,
            }
            for g in inp.grants
        ],
        "ticket_id": inp.ticket_id,
        "correlation_id": inp.correlation_id,
    }
    port.notify_provisioned(payload)
    return connection
