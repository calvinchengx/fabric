from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

_WORKSPACE_ROLES = frozenset({"Admin", "Member", "Contributor", "Viewer"})


class GroupRoleSpec(BaseModel):
    object_id: str = Field(description="Microsoft Entra group object ID")
    role: str = Field(description="Fabric workspace role")

    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, v: str) -> str:
        if v not in _WORKSPACE_ROLES:
            msg = f"role must be one of {sorted(_WORKSPACE_ROLES)}"
            raise ValueError(msg)
        return v


class ServicePrincipalRoleSpec(BaseModel):
    object_id: str = Field(description="Microsoft Entra service principal object ID")
    role: str = Field(description="Fabric workspace role")

    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, v: str) -> str:
        if v not in _WORKSPACE_ROLES:
            msg = f"role must be one of {sorted(_WORKSPACE_ROLES)}"
            raise ValueError(msg)
        return v


class UpdateWorkspaceRoleAssignmentRequest(BaseModel):
    """Body for PATCH workspace role assignment (Fabric Core API)."""

    role: str = Field(description="Fabric workspace role")
    ticket_id: str | None = None
    correlation_id: str | None = None

    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, v: str) -> str:
        if v not in _WORKSPACE_ROLES:
            msg = f"role must be one of {sorted(_WORKSPACE_ROLES)}"
            raise ValueError(msg)
        return v


class ProvisionWorkspaceRequest(BaseModel):
    display_name: str = Field(max_length=256)
    description: str | None = Field(default=None, max_length=4000)
    capacity_id: str | None = None
    domain_id: str | None = None
    group_assignments: list[GroupRoleSpec] = Field(default_factory=list)
    spn_assignments: list[ServicePrincipalRoleSpec] = Field(
        default_factory=list,
        description="Service principals to add as workspace role assignments (automation).",
    )
    ticket_id: str | None = None
    correlation_id: str | None = None


_CONNECTION_ROLES = frozenset({"Owner", "UserWithReshare", "User"})


class SqlBasicCredentialBody(BaseModel):
    username: str
    password: str


class SqlServicePrincipalCredentialBody(BaseModel):
    tenant_id: str
    client_id: str
    client_secret: str


class ConnectionGrantSpec(BaseModel):
    object_id: str = Field(description="Entra object id for User, Group, or ServicePrincipal")
    principal_type: Literal["User", "Group", "ServicePrincipal"]
    role: str = Field(description="Fabric connection role")

    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, v: str) -> str:
        if v not in _CONNECTION_ROLES:
            msg = f"role must be one of {sorted(_CONNECTION_ROLES)}"
            raise ValueError(msg)
        return v


class CreateSqlConnectionRequest(BaseModel):
    """Shareable cloud SQL connection (Fabric warehouse / Azure SQL) + optional grants."""

    display_name: str = Field(max_length=200)
    server: str = Field(
        description="SQL server hostname (e.g. *.datawarehouse.pbidedicated.windows.net)",
    )
    database: str = Field(description="Database name (warehouse name)")
    basic: SqlBasicCredentialBody | None = None
    service_principal: SqlServicePrincipalCredentialBody | None = None
    grants: list[ConnectionGrantSpec] = Field(default_factory=list)
    ticket_id: str | None = None
    correlation_id: str | None = None
    privacy_level: str = "Organizational"
    allow_usage_in_user_controlled_code: bool = False
    skip_test_connection: bool = False

    @model_validator(mode="after")
    def exactly_one_credential_kind(self) -> CreateSqlConnectionRequest:
        has_basic = self.basic is not None
        has_spn = self.service_principal is not None
        if has_basic == has_spn:
            msg = "Provide exactly one of `basic` or `service_principal` credential objects"
            raise ValueError(msg)
        return self
