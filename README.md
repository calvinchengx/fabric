# fabric-provisioner

Thin **Python** layer for **Microsoft Fabric**: create **workspaces** and [workspace role assignments](https://learn.microsoft.com/en-us/rest/api/fabric/core/workspaces/add-workspace-role-assignment) (Entra **groups** / **SPNs**), create **shareable SQL connections** ([Connections API](https://learn.microsoft.com/en-us/rest/api/fabric/core/connections/create-connection)) for warehouse-style endpoints with **User / Group / SPN** [connection roles](https://learn.microsoft.com/en-us/rest/api/fabric/core/connections/add-connection-role-assignment), emit **audit** JSON lines, and optionally **POST** to a webhook.

**Policy** (who should have access) belongs in **Entra** (groups, access packages, lifecycle). This app **applies** approved outcomes — it does not replace IAM governance.

## Documentation

Design and operations for **Fabric administrators** and this app live in **[`docs/`](docs/)**:

| Document | Description |
|----------|-------------|
| **[docs/README.md](docs/README.md)** | Index and scope |
| **[docs/get-started.md](docs/get-started.md)** | **Get started** — install, `.env`, first `just health` |
| **[docs/usage.md](docs/usage.md)** | **How to run** — CLI, HTTP, `curl`, audit examples |
| **[docs/permissions.md](docs/permissions.md)** | **Permissions & least privilege** — client credentials, Fabric/Entra requirements |
| **[docs/architecture.md](docs/architecture.md)** | Entra vs Fabric, Fabric APIs, tenant prerequisites |
| **[docs/governance.md](docs/governance.md)** | Roles, operations, security, checklists |

**On GitHub:** open the [`docs/`](docs/) folder in the repo. GitHub shows **`docs/README.md`** under the file list (same behavior as the root **`README.md`**). Click any `.md` file to read it with Markdown rendering.

**GitHub Pages (MkDocs site):** the repository includes [`mkdocs.yml`](mkdocs.yml) and [`.github/workflows/docs.yml`](.github/workflows/docs.yml). After you enable **Settings → Pages → Build and deployment → Source: GitHub Actions**, pushes to `main` (or `master`) that touch `docs/` or `mkdocs.yml` build and publish the site. The live URL is usually `https://<owner>.github.io/<repo>/` (also under **Settings → Pages**). Local preview:

```bash
uv sync --group docs
uv run mkdocs serve
# or: just docs
```

Set **`repo_url`** (and optional **`site_url`**) in [`mkdocs.yml`](mkdocs.yml) if your GitHub remote is not `calvinchengx/fabric`.

**Optional:** In the repository **About** settings, set **Website** to the Pages URL or to `docs/README.md` on GitHub.

**Note:** When the HTTP server is running, **`/docs`** is **Swagger UI** for this API—not the same as the **`docs/`** folder in git.

## Requirements

- Python **3.11+**
- [uv](https://docs.astral.sh/uv/)
- An **Entra app registration** with client secret (or adapt `auth.py` for certificates)
- Tenant settings allowing the identity to **create workspaces** and **connections** and call **Fabric APIs** (see [service principals and Fabric](https://learn.microsoft.com/en-us/fabric/admin/service-admin-portal-developer)); required scopes/permissions depend on your auth model and admin policy (for example `Connection.ReadWrite.All` for connection role APIs)

## Setup

```bash
cd fabric   # or your clone directory
uv sync --all-groups
cp .env.example .env   # fill in secrets
```

**Editors:** Point Python analysis at **`.venv`** (e.g. *Python: Select Interpreter*). The repo sets `[tool.pyright]` in `pyproject.toml` so Pylance/Pyright resolve third-party imports after `uv sync`.

**Shorter commands (optional):** install **[just](https://github.com/casey/just)** and use **`just health`**, **`just docs`**, **`just api`**, etc. — see **`justfile`** and **[CONTRIBUTING.md](CONTRIBUTING.md#short-commands-with-just)**.

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
| `VALIDATE_GROUP_IDS_WITH_GRAPH` | no | If `true`, `GET /groups/{id}` and `GET /servicePrincipals/{id}` (for SPN assignments) before Fabric role calls |
| `INTEGRATION_WEBHOOK_URL` | no | HTTPS URL for JSON POST after provision |
| `AUDIT_JSONL_PATH` | no | Append one JSON audit record per line |

Field names in code use lowercase aliases from pydantic-settings (e.g. `azure_tenant_id` reads `AZURE_TENANT_ID`).

When **`INTEGRATION_WEBHOOK_URL`** is set, the provisioner **POST**s JSON after success. Workspace runs include `workspace`, `group_assignments`, `spn_assignments`, `ticket_id`, `correlation_id`. SQL connection runs use `operation: sql_shareable_connection`, `connection`, `grants`, `ticket_id`, `correlation_id`.

Optional **CLI-only** env vars for secrets (avoid argv): `FABRIC_SQL_CONNECTION_PASSWORD`, `FABRIC_SQL_AUTH_CLIENT_SECRET`.

## CLI

**Discover commands** (Typer): run **`uv run fabric-provision --help`** for subcommands, and **`uv run fabric-provision <command> --help`** for flags (e.g. `create-workspace --help`).

| Command | What it does |
|--------|----------------|
| `health` | Acquire a Fabric API token (validates Entra app + env). |
| `create-workspace` | Create a workspace; optional `--group-id` / `--group-role`, `--spn-id` / `--spn-role`, `--capacity-id`, `--domain-id`, `--ticket-id`, etc. |
| `create-sql-connection` | [Shareable cloud SQL](https://learn.microsoft.com/en-us/rest/api/fabric/core/connections/create-connection) connection; `--server`, `--database`, SQL **basic** or **AAD SPN** auth to the data source; optional `--grant-user-id`, `--grant-group-id`, `--grant-spn-id` with connection roles `Owner` / `UserWithReshare` / `User`. |
| `audit-dump` | Stream JSONL audit to stdout; `--path` or `AUDIT_JSONL_PATH`; optional `--tail N`. |

Examples:

```bash
uv run fabric-provision health
uv run fabric-provision create-workspace "Analytics — Finance" \
  --group-id <entra-group-object-id> \
  --group-role Member \
  --ticket-id CHG12345
# Optional automation principal on the same workspace (Entra service principal object ID):
uv run fabric-provision create-workspace "ETL — Prod" \
  --spn-id <entra-spn-object-id> \
  --spn-role Contributor \
  --correlation-id req-etl-001
# Shareable SQL connection (Fabric warehouse / SQL endpoint) + grant a group connection access:
uv run fabric-provision create-sql-connection \
  --server '<warehouse>.datawarehouse.pbidedicated.windows.net' \
  --database '<warehouse_name>' \
  --sql-username '<sql_user>' \
  --grant-group-id <entra-group-object-id> \
  --grant-group-role User \
  'Catalog — DW read'
# Shareable SQL connection using AAD service principal credentials for SQL auth:
uv run fabric-provision create-sql-connection \
  --server '<warehouse>.datawarehouse.pbidedicated.windows.net' \
  --database '<warehouse_name>' \
  --sql-auth-tenant-id '<tenant-guid>' \
  --sql-auth-client-id '<app-client-guid>' \
  --sql-auth-client-secret '<app-secret>' \
  --grant-spn-id <entra-spn-object-id> \
  --grant-spn-role UserWithReshare \
  'Catalog — DW automation'
```

For safer secret handling with these SQL examples, prefer env vars
`FABRIC_SQL_CONNECTION_PASSWORD` and `FABRIC_SQL_AUTH_CLIENT_SECRET`
instead of passing secrets as CLI flags.

**Traceability:** pass **`--ticket-id`** (change/catalog id, e.g. ServiceNow, BMC Helix, Jira) and/or **`--correlation-id`** (request/run id). The same fields exist on **`POST /v1/workspaces`** and **`POST /v1/connections/sql`**; the app does not validate tickets against external systems - it records them in audit output and webhooks.

## HTTP API

```bash
uv run uvicorn fabric_provisioner.api:app --host 0.0.0.0 --port 8080
```

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/healthz` | Liveness (`{"status": "ok"}`); does not call Fabric. |
| `POST` | `/v1/workspaces` | Create workspace and apply group and optional SPN role assignments (same behavior as CLI). |
| `POST` | `/v1/connections/sql` | Create shareable SQL connection + optional connection role grants (JSON body; see OpenAPI `/docs`). |

With the server running, interactive **OpenAPI** is at **`/docs`** (Swagger UI) and **`/redoc`**.

`POST /v1/workspaces` with JSON body (`group_assignments` and `spn_assignments` default to empty; omit or use `[]` if unused):

```json
{
  "display_name": "Analytics — Finance",
  "description": "Provisioned from catalog",
  "capacity_id": null,
  "domain_id": null,
  "group_assignments": [
    { "object_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "role": "Member" }
  ],
  "spn_assignments": [
    { "object_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", "role": "Contributor" }
  ],
  "ticket_id": "CHG12345",
  "correlation_id": "req-abc"
}
```

`POST /v1/connections/sql` — provide **exactly one** of `basic` or `service_principal` for credentials **to SQL** (not the provisioner app). Example (passwords belong in secret stores for production; see Microsoft Learn for Key Vault references):

```json
{
  "display_name": "Warehouse link",
  "server": "x.datawarehouse.pbidedicated.windows.net",
  "database": "MyWarehouse",
  "basic": { "username": "sql_reader", "password": "…" },
  "grants": [
    {
      "object_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
      "principal_type": "Group",
      "role": "User"
    },
    {
      "object_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
      "principal_type": "ServicePrincipal",
      "role": "UserWithReshare"
    }
  ],
  "ticket_id": "CHG1",
  "skip_test_connection": false
}
```

## Logs and extraction

### What this app logs (provisioner-only)

Every successful **workspace create/role assignment** and **SQL connection create/role assignment** step emits:

- **One JSON object per line** on **stdout** (`event`, `ts`, `workspace_id`, `ticket_id`, etc.). Events include `workspace.created`, `workspace.group_assigned`, `workspace.spn_assigned`, `connection.sql.created`, `connection.role_assigned`.
- If **`AUDIT_JSONL_PATH`** is set, the **same** records are **appended** to that file (JSON Lines).

**Extract / forward** for your SIEM or object storage:

- **Containers / Kubernetes:** ship **stdout** with your cluster log collector (Fluent Bit, Datadog, Splunk, etc.).
- **VM / cron:** set `AUDIT_JSONL_PATH` and **tail** or **copy** the file on a schedule, or stream it:

```bash
uv run fabric-provision audit-dump --path ./var/audit.jsonl > export.jsonl
uv run fabric-provision audit-dump --path ./var/audit.jsonl --tail 500
# With AUDIT_JSONL_PATH in .env, path can be omitted:
uv run fabric-provision audit-dump | jq -c 'select(.event=="workspace.created")'
uv run fabric-provision audit-dump | jq -c 'select(.event=="workspace.spn_assigned")'
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

Unit tests live under **`tests/`**: workspace flow (`test_service.py`), SQL connection flow (`test_connections.py`), Pydantic models (`test_models.py`). The **CLI** and **FastAPI** layers are not integration-tested; use the commands above for line coverage.

## Extending

The library exposes:

- Workspace role assignment via `FabricClient.add_workspace_role_assignment` (`Group`, `ServicePrincipal`, etc.; see [Add Workspace Role Assignment](https://learn.microsoft.com/en-us/rest/api/fabric/core/workspaces/add-workspace-role-assignment)). **CLI/API:** `--spn-id` / `--spn-role` or `spn_assignments` in JSON.
- Connection lifecycle via `FabricClient.create_connection` and connection grants via `FabricClient.add_connection_role_assignment` (`User`, `Group`, `ServicePrincipal`; see [Create Connection](https://learn.microsoft.com/en-us/rest/api/fabric/core/connections/create-connection) and [Add Connection Role Assignment](https://learn.microsoft.com/en-us/rest/api/fabric/core/connections/add-connection-role-assignment)). **CLI/API:** `create-sql-connection` flags (`--grant-user-id`, `--grant-group-id`, `--grant-spn-id`) or `grants` on `POST /v1/connections/sql`.

Prefer **groups** for human access and **scoped SPNs** for automation identities.

## License

[MIT](LICENSE) — see `LICENSE` for the full text.
