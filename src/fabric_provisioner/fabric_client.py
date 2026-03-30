from __future__ import annotations

import time
from typing import Any

import httpx

# Workspace roles for Fabric Core roleAssignments API (Microsoft Learn).
WorkspaceRole = str  # Admin | Member | Contributor | Viewer


class FabricClient:
    """Fabric Core REST client (workspaces, role assignments, connections, inventory reads)."""

    _MAX_429_RETRIES = 5
    _MAX_RETRY_AFTER_SEC = 120

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

    def _request_get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        """GET with basic 429 / Retry-After handling (Microsoft Fabric pagination APIs)."""
        attempt = 0
        while True:
            response = self._client.get(path, params=params)
            if response.status_code == 429:
                attempt += 1
                if attempt >= self._MAX_429_RETRIES:
                    response.raise_for_status()
                wait = min(
                    int(response.headers.get("Retry-After", "60")),
                    self._MAX_RETRY_AFTER_SEC,
                )
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response.json()

    def list_workspaces_page(
        self,
        *,
        continuation_token: str | None = None,
        roles: str | None = None,
        prefer_workspace_specific_endpoints: bool | None = None,
    ) -> dict[str, Any]:
        """
        GET /workspaces — one page. See
        https://learn.microsoft.com/en-us/rest/api/fabric/core/workspaces/list-workspaces
        """
        params: dict[str, str] = {}
        if continuation_token:
            params["continuationToken"] = continuation_token
        if roles:
            params["roles"] = roles
        if prefer_workspace_specific_endpoints is not None:
            params["preferWorkspaceSpecificEndpoints"] = (
                "true" if prefer_workspace_specific_endpoints else "false"
            )
        return self._request_get("/workspaces", params=params or None)

    def list_workspace_items_page(
        self,
        workspace_id: str,
        *,
        continuation_token: str | None = None,
        recursive: bool = True,
        item_type: str | None = None,
    ) -> dict[str, Any]:
        """
        GET /workspaces/{id}/items — one page. See
        https://learn.microsoft.com/en-us/rest/api/fabric/core/items/list-items
        """
        params: dict[str, str] = {
            "recursive": "true" if recursive else "false",
        }
        if continuation_token:
            params["continuationToken"] = continuation_token
        if item_type:
            params["type"] = item_type
        return self._request_get(f"/workspaces/{workspace_id}/items", params=params)

    def list_workspace_role_assignments_page(
        self,
        workspace_id: str,
        *,
        continuation_token: str | None = None,
    ) -> dict[str, Any]:
        """
        GET /workspaces/{id}/roleAssignments — one page. See
        https://learn.microsoft.com/en-us/rest/api/fabric/core/workspaces/list-workspace-role-assignments
        """
        params: dict[str, str] = {}
        if continuation_token:
            params["continuationToken"] = continuation_token
        return self._request_get(
            f"/workspaces/{workspace_id}/roleAssignments",
            params=params or None,
        )

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

    def update_workspace_role_assignment(
        self,
        *,
        workspace_id: str,
        workspace_role_assignment_id: str,
        role: WorkspaceRole,
    ) -> dict[str, Any]:
        """
        PATCH an existing workspace role assignment (role only).

        See https://learn.microsoft.com/en-us/rest/api/fabric/core/workspaces/update-workspace-role-assignment
        """
        response = self._client.patch(
            f"/workspaces/{workspace_id}/roleAssignments/{workspace_role_assignment_id}",
            json={"role": role},
        )
        response.raise_for_status()
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
