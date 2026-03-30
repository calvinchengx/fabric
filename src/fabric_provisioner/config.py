from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Load from environment / `.env`. See `.env.example`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    azure_tenant_id: str = Field(description="Microsoft Entra tenant ID")
    azure_client_id: str = Field(description="App registration client ID")
    azure_client_secret: str = Field(description="App registration client secret")

    fabric_api_scope: str = "https://api.fabric.microsoft.com/.default"
    graph_api_scope: str = "https://graph.microsoft.com/.default"

    fabric_api_base: str = "https://api.fabric.microsoft.com/v1"
    graph_api_base: str = "https://graph.microsoft.com/v1.0"

    validate_group_ids_with_graph: bool = Field(
        default=False,
        description=(
            "If true, verify each Entra group and service principal (when assigned) exists "
            "via Microsoft Graph before workspace role assignments."
        ),
    )

    integration_webhook_url: str | None = Field(
        default=None,
        description=(
            "Optional HTTPS URL to POST JSON after provisioning (ticket/catalog hook)."
        ),
    )

    audit_jsonl_path: Path | None = Field(
        default=None,
        description="If set, append one JSON object per line for audit events.",
    )

    inventory_enabled: bool = Field(
        default=True,
        alias="FABRIC_INVENTORY_ENABLED",
        description="If false, inventory CLI subcommands and HTTP routes are disabled.",
    )
    inventory_workspace_allowlist: str | None = Field(
        default=None,
        alias="FABRIC_INVENTORY_WORKSPACE_ALLOWLIST",
        description=(
            "Optional comma-separated Fabric workspace UUIDs. When set, inventory may only "
            "crawl workspaces in this set (intersected with request/CLI filters)."
        ),
    )

    def parsed_inventory_workspace_allowlist(self) -> frozenset[str] | None:
        """Non-empty frozenset of workspace IDs from ``inventory_workspace_allowlist``, or None."""
        raw = self.inventory_workspace_allowlist
        if raw is None or not raw.strip():
            return None
        ids = frozenset(p.strip() for p in raw.split(",") if p.strip())
        return ids if ids else None


def load_settings() -> Settings:
    """Build settings from process env and optional ``.env`` (see ``Settings``)."""
    # BaseSettings fills required fields from env; Pyright cannot see that.
    return Settings()  # pyright: ignore[reportCallIssue]
