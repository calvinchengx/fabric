from __future__ import annotations

from typing import Any

import httpx

# Workspace roles for Fabric Core roleAssignments API (Microsoft Learn).
WorkspaceRole = str  # Admin | Member | Contributor | Viewer


class FabricClient:
    """Minimal Fabric Core REST client (workspaces + role assignments)."""

    def __init__(self, *, base_url: str, access_token: str, timeout: float = 60.0) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> FabricClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def create_workspace(
        self,
        *,
        display_name: str,
        description: str | None = None,
        capacity_id: str | None = None,
        domain_id: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"displayName": display_name}
        if description is not None:
            body["description"] = description
        if capacity_id is not None:
            body["capacityId"] = capacity_id
        if domain_id is not None:
            body["domainId"] = domain_id

        response = self._client.post("/workspaces", json=body)
        response.raise_for_status()
        return response.json()

    def add_workspace_role_assignment(
        self,
        *,
        workspace_id: str,
        principal_id: str,
        principal_type: str,
        role: WorkspaceRole,
    ) -> dict[str, Any] | None:
        """
        Add a workspace role assignment.

        principal_type examples: Group, User, ServicePrincipal (per Fabric REST docs).
        """
        payload = {
            "principal": {"id": principal_id, "type": principal_type},
            "role": role,
        }
        response = self._client.post(
            f"/workspaces/{workspace_id}/roleAssignments",
            json=payload,
        )
        response.raise_for_status()
        if not response.content:
            return None
        return response.json()

    def create_connection(self, body: dict[str, Any]) -> dict[str, Any]:
        """POST /connections (ShareableCloud, gateway, etc. — see Microsoft Fabric REST)."""
        response = self._client.post("/connections", json=body)
        response.raise_for_status()
        return response.json()

    def add_connection_role_assignment(
        self,
        *,
        connection_id: str,
        principal: dict[str, Any],
        role: str,
    ) -> dict[str, Any]:
        """POST /connections/{id}/roleAssignments — User, Group, ServicePrincipal, …"""
        payload = {"principal": principal, "role": role}
        response = self._client.post(
            f"/connections/{connection_id}/roleAssignments",
            json=payload,
        )
        response.raise_for_status()
        return response.json()
