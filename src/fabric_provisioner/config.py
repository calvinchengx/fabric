from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Load from environment / `.env`. See `.env.example`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
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


def load_settings() -> Settings:
    """Build settings from process env and optional ``.env`` (see ``Settings``)."""
    # BaseSettings fills required fields from env; Pyright cannot see that.
    return Settings()  # pyright: ignore[reportCallIssue]
