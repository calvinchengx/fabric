from __future__ import annotations

from typing import Any

import httpx


class GraphClient:
    """Minimal Microsoft Graph client for optional validation."""

    def __init__(self, *, base_url: str, access_token: str, timeout: float = 60.0) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> GraphClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def get_group(self, group_object_id: str) -> dict[str, Any]:
        response = self._client.get(f"/groups/{group_object_id}")
        response.raise_for_status()
        return response.json()
