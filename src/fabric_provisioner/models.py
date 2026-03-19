from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

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


class ProvisionWorkspaceRequest(BaseModel):
    display_name: str = Field(max_length=256)
    description: str | None = Field(default=None, max_length=4000)
    capacity_id: str | None = None
    domain_id: str | None = None
    group_assignments: list[GroupRoleSpec] = Field(default_factory=list)
    ticket_id: str | None = None
    correlation_id: str | None = None
