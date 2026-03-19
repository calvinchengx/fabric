# fabric-provisioner

Thin **Python** layer for **Microsoft Fabric** workspace provisioning: create workspaces via the [Fabric Core REST API](https://learn.microsoft.com/en-us/rest/api/fabric/core/workspaces/create-workspace), assign **Entra security groups** with [workspace role assignments](https://learn.microsoft.com/en-us/rest/api/fabric/core/workspaces/add-workspace-role-assignment), emit **structured audit** lines, and optionally **POST** results to a webhook (ticket/catalog integration).

**Policy** (who should have access) belongs in **Entra** (groups, access packages, lifecycle). This app **applies** approved outcomes — it does not replace IAM governance.

See **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** for principles and data flow, and **[docs/GOVERNANCE.md](docs/GOVERNANCE.md)** for how we expect to **govern**, **operate**, and **secure** Fabric and this provisioner.

## Requirements

- Python **3.11+**
- [uv](https://docs.astral.sh/uv/)
- An **Entra app registration** with client secret (or adapt `auth.py` for certificates)
- Tenant settings allowing the identity to **create workspaces** and call **Fabric APIs** (see Microsoft Learn for [service principals and Fabric](https://learn.microsoft.com/en-us/fabric/admin/service-admin-portal-developer))

## Setup

```bash
cd fabric   # or your clone directory
uv sync --all-groups
cp .env.example .env   # fill in secrets
```

**Editors:** Point Python analysis at **`.venv`** (e.g. *Python: Select Interpreter*). The repo sets `[tool.pyright]` in `pyproject.toml` so Pylance/Pyright resolve third-party imports after `uv sync`.

## Configuration

Environment variables (also loadable from `.env` in the working directory):

| Variable | Required | Description |
|----------|----------|-------------|
| `AZURE_TENANT_ID` | yes | Entra tenant ID |
| `AZURE_CLIENT_ID` | yes | App registration client ID |
| `AZURE_CLIENT_SECRET` | yes | App registration client secret |
| `FABRIC_API_SCOPE` | no | Default `https://api.fabric.microsoft.com/.default` |
| `GRAPH_API_SCOPE` | no | Default `https://graph.microsoft.com/.default` |
| `FABRIC_API_BASE` | no | Default `https://api.fabric.microsoft.com/v1` |
| `GRAPH_API_BASE` | no | Default `https://graph.microsoft.com/v1.0` |
| `VALIDATE_GROUP_IDS_WITH_GRAPH` | no | If `true`, `GET /groups/{id}` before assigning roles |
| `INTEGRATION_WEBHOOK_URL` | no | HTTPS URL for JSON POST after provision |
| `AUDIT_JSONL_PATH` | no | Append one JSON audit record per line |

Field names in code use lowercase aliases from pydantic-settings (e.g. `azure_tenant_id` reads `AZURE_TENANT_ID`).

## CLI

```bash
uv run fabric-provision health
uv run fabric-provision create-workspace "Analytics — Finance" \
  --group-id <entra-group-object-id> \
  --group-role Member \
  --ticket-id CHG12345
```

## HTTP API

```bash
uv run uvicorn fabric_provisioner.api:app --host 0.0.0.0 --port 8080
```

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/healthz` | Liveness (`{"status": "ok"}`); does not call Fabric. |
| `POST` | `/v1/workspaces` | Create workspace and apply group role assignments (same behavior as CLI). |

`POST /v1/workspaces` with JSON body:

```json
{
  "display_name": "Analytics — Finance",
  "description": "Provisioned from catalog",
  "capacity_id": null,
  "domain_id": null,
  "group_assignments": [
    { "object_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "role": "Member" }
  ],
  "ticket_id": "CHG12345",
  "correlation_id": "req-abc"
}
```

## Logs and extraction

### What this app logs (provisioner-only)

Every successful **create workspace** / **group assignment** step emits:

- **One JSON object per line** on **stdout** (`event`, `ts`, `workspace_id`, `ticket_id`, etc.).
- If **`AUDIT_JSONL_PATH`** is set, the **same** records are **appended** to that file (JSON Lines).

**Extract / forward** for your SIEM or object storage:

- **Containers / Kubernetes:** ship **stdout** with your cluster log collector (Fluent Bit, Datadog, Splunk, etc.).
- **VM / cron:** set `AUDIT_JSONL_PATH` and **tail** or **copy** the file on a schedule, or stream it:

```bash
uv run fabric-provision audit-dump --path ./var/audit.jsonl > export.jsonl
uv run fabric-provision audit-dump --path ./var/audit.jsonl --tail 500
# With AUDIT_JSONL_PATH in .env, path can be omitted:
uv run fabric-provision audit-dump | jq -c 'select(.event=="workspace.created")'
```

### Fabric-wide activity (not this repo)

**User actions, refreshes, and sign-ins across Fabric** are **not** pulled by `fabric-provisioner`. Use Microsoft’s platforms for tenant audit — for example **Microsoft Purview** / **Microsoft 365 audit** / **Power BI activity** (and Fabric admin monitoring as your org enables them). Wire those exports into the same SIEM if you want a **single pane** next to provisioner JSONL.

## Tests

```bash
uv run pytest
uv run pytest --cov=fabric_provisioner --cov-report=term-missing
uv run pytest --cov=fabric_provisioner --cov-report=html   # open htmlcov/index.html
uv run ruff check src tests
```

Unit tests live under **`tests/`** and mock Fabric/token calls (`test_service.py`) plus Pydantic models (`test_models.py`). The **CLI** and **FastAPI** layers are not covered yet; use the commands above for line coverage of `src/fabric_provisioner/`.

## Extending

The library exposes `FabricClient.add_workspace_role_assignment` with a `principal_type` string. For automation SPNs on a workspace, Microsoft’s API expects a service principal principal type (see [Add Workspace Role Assignment](https://learn.microsoft.com/en-us/rest/api/fabric/core/workspaces/add-workspace-role-assignment)); add CLI/API fields only if your governance model needs it — prefer **groups** for humans and **scoped SPNs** for jobs.

## License

[MIT](LICENSE) — see `LICENSE` for the full text.
