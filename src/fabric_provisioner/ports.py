from __future__ import annotations

import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class TicketCatalogPort(Protocol):
    """Outbound hook after provisioning (ServiceNow, Jira, internal catalog, etc.)."""

    def notify_provisioned(self, payload: dict[str, Any]) -> None:
        """Fire-and-forget style; implementations should swallow or log errors."""


class NoOpTicketCatalogPort:
    def notify_provisioned(self, payload: dict[str, Any]) -> None:  # noqa: ARG002
        return


class WebhookTicketCatalogPort:
    """POST JSON to a fixed URL; disabled if url is None."""

    def __init__(self, url: str | None, timeout: float = 30.0) -> None:
        self._url = url
        self._timeout = timeout

    def notify_provisioned(self, payload: dict[str, Any]) -> None:
        if not self._url:
            return
        import httpx

        try:
            httpx.post(self._url, json=payload, timeout=self._timeout)
        except httpx.HTTPError as exc:
            logger.warning("integration webhook failed: %s", exc)
