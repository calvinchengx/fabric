# How to use fabric-provisioner

This page is a **practical guide**: install, configure, and run the **CLI** and **HTTP API** with concrete examples. New to the project? Follow **[get-started.md](get-started.md)** first. For design and tenant policy, see [architecture.md](architecture.md), [permissions.md](permissions.md) (what Entra/Fabric must grant), and [governance.md](governance.md).

**Commands:** examples below use **[just](https://github.com/casey/just)** recipes from the repo **`justfile`** (`just sync`, `just health`, `just cli …`, `just api`, `just docs`). Install **just** per **[CONTRIBUTING.md](https://github.com/calvinchengx/fabric/blob/main/CONTRIBUTING.md#short-commands-with-just)**. **Without just**, run the same flows with **`uv sync --all-groups`**, **`uv run fabric-provision …`**, and **`uv run uvicorn …`** (see the [root README](https://github.com/calvinchengx/fabric/blob/main/README.md#cli)).

**Identity model:** the tool uses **OAuth 2.0 client credentials** (an Entra **app registration**). Every Fabric call runs as that application (your **provisioner** service principal), not as your personal user. Your org must allow that identity to use Fabric APIs and to perform the operations you need (workspace create, role assignments, connections, etc.).

---

## 1. Install and configure

From the repository root:

```bash
just sync
cp .env.example .env
```

(`just sync` runs **`uv sync --all-groups`**.)

Edit **`.env`** with your tenant and app (minimum):

| Variable | Purpose |
|----------|---------|
| `AZURE_TENANT_ID` | Entra tenant ID |
| `AZURE_CLIENT_ID` | App registration (client) ID |
| `AZURE_CLIENT_SECRET` | Client secret for that app |

Optional variables (defaults are usually fine) are listed in **`.env.example`** at the repository root and in the [configuration table in the root README](https://github.com/calvinchengx/fabric/blob/main/README.md#configuration).

**Editors:** after sync, select the project **`.venv`** as the Python interpreter so imports resolve.

### Preview this documentation site (MkDocs)

```bash
just docs
```

Usually **http://127.0.0.1:8000** (live reload). The recipe runs **`uv sync --group docs`** then **`mkdocs serve`**.

---

## 2. Check that Fabric auth works

This acquires a token for `FABRIC_API_SCOPE` (default `https://api.fabric.microsoft.com/.default`) and fails fast if credentials or tenant policy are wrong.

```bash
just health
```

You should see a short **ok** message. If this fails, fix Entra secrets and Fabric **developer / service principal** settings before trying workspace or connection commands (see **Tenant prerequisites** under [APIs in use](architecture.md#apis-in-use) in architecture.md).

---

## 3. CLI examples

Discover flags anytime with:

```bash
just cli --help
just cli create-workspace --help
```

Workspace roles for groups and SPNs are always one of: **`Admin`**, **`Member`**, **`Contributor`**, **`Viewer`**.

### Create a workspace (display name only)

```bash
just cli create-workspace "My team workspace"
```

The JSON printed to the console is the **Fabric workspace** object (includes `id` — the workspace UUID).

### Create a workspace and assign one Entra group (`Member`)

Replace the placeholder with your **group object ID** (Entra ID → Groups → group → Object Id).

```bash
just cli create-workspace "Analytics — Finance" \
  --group-id "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee" \
  --group-role Member \
  --ticket-id CHG12345 \
  --correlation-id run-2026-03-31-01
```

### Multiple groups, same role

Repeat **`--group-id`**; every group gets **`--group-role`** (default `Member` if omitted).

```bash
just cli create-workspace "Shared reporting" \
  --group-id "11111111-1111-1111-1111-111111111111" \
  --group-id "22222222-2222-2222-2222-222222222222" \
  --group-role Viewer
```

### Add a service principal to the workspace (automation)

Use the Entra **service principal object ID** (not the app registration “Application ID” unless they match in your directory).

```bash
just cli create-workspace "ETL — Prod" \
  --spn-id "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb" \
  --spn-role Contributor
```

You can combine **`--group-id`** and **`--spn-id`** on the same run.

### Optional capacity and domain

```bash
just cli create-workspace "Capacity-bound workspace" \
  --capacity-id "cccccccc-cccc-cccc-cccc-cccccccccccc" \
  --domain-id "dddddddd-dddd-dddd-dddd-dddddddddddd"
```

### Change an existing workspace role assignment

This calls Fabric **[Update Workspace Role Assignment](https://learn.microsoft.com/en-us/rest/api/fabric/core/workspaces/update-workspace-role-assignment)**. You need:

1. **`workspace_id`** — Fabric workspace UUID.
2. **`assignment_id`** — Fabric **role assignment** UUID (the `id` field on a role assignment), **not** the Entra principal object id.

**Where to get `assignment_id`:** from the JSON returned when the assignment was created, from Fabric’s **List workspace role assignments** REST API, or from admin/ops tooling your org uses. The provisioner CLI does not list assignments today.

The identity configured in **`.env`** must be a **workspace admin**. Microsoft does not allow changing the role of the **last** workspace admin via this API.

```bash
just cli update-workspace-role \
  "0ac682f5-aee3-4968-9d21-692eb3fd4056" \
  "0218b8c4-f5a2-4a1e-bbbd-a986dd8aeb81" \
  --role Contributor \
  --ticket-id CHG99999
```

### Shareable SQL connection (SQL login) + grant a group on the connection

Connection roles are **`Owner`**, **`UserWithReshare`**, **`User`** (different from workspace roles). Prefer **`FABRIC_SQL_CONNECTION_PASSWORD`** in `.env` instead of **`--sql-password`** on the command line.

```bash
export FABRIC_SQL_CONNECTION_PASSWORD='your-secret-here'

just cli create-sql-connection \
  --server 'mywarehouse.datawarehouse.pbidedicated.windows.net' \
  --database 'MyWarehouse' \
  --sql-username 'sql_reader' \
  --grant-group-id 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee' \
  --grant-group-role User \
  'Catalog — DW read'
```

The last argument is the **connection display name** in Fabric.

### Shareable SQL connection (Entra app auth to SQL) + grant an SPN

```bash
export FABRIC_SQL_AUTH_CLIENT_SECRET='sql-app-secret-here'

just cli create-sql-connection \
  --server 'mywarehouse.datawarehouse.pbidedicated.windows.net' \
  --database 'MyWarehouse' \
  --sql-auth-tenant-id 'your-tenant-guid' \
  --sql-auth-client-id 'sql-app-client-id-guid' \
  --sql-auth-client-secret "$FABRIC_SQL_AUTH_CLIENT_SECRET" \
  --grant-spn-id 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb' \
  --grant-spn-role UserWithReshare \
  'Catalog — DW automation'
```

### Read audit JSONL

If **`AUDIT_JSONL_PATH`** is set, each successful step appends one JSON object per line. Stream or filter:

```bash
just cli audit-dump --path ./var/audit.jsonl --tail 100

# With AUDIT_JSONL_PATH in .env you can omit --path when it matches
just cli audit-dump | jq -c 'select(.event=="workspace.created")'
```

Events include `workspace.created`, `workspace.group_assigned`, `workspace.spn_assigned`, `workspace.role_assignment_updated`, `connection.sql.created`, `connection.role_assigned`, etc.

---

## 4. HTTP API examples

Start the HTTP API (default **127.0.0.1:8080**):

```bash
just api
```

Use **`just api 3000`** (or another port) to change the port. **`just api`** binds **`127.0.0.1`** only. For **`0.0.0.0`** (containers or LAN access), run **`uv run uvicorn fabric_provisioner.api:app --host 0.0.0.0 --port 8080`**.

Interactive OpenAPI (Swagger) is at **`http://127.0.0.1:8080/docs`** (adjust host/port if you changed them). **`GET /healthz`** does not call Fabric.

### Create a workspace (`POST /v1/workspaces`)

```bash
curl -sS -X POST 'http://127.0.0.1:8080/v1/workspaces' \
  -H 'Content-Type: application/json' \
  -d '{
    "display_name": "Analytics — Finance",
    "description": "From automation",
    "capacity_id": null,
    "domain_id": null,
    "group_assignments": [
      { "object_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "role": "Member" }
    ],
    "spn_assignments": [],
    "ticket_id": "CHG12345",
    "correlation_id": "api-req-1"
  }'
```

### Update a workspace role assignment (`PATCH`)

Path pattern: **`/v1/workspaces/{workspace_id}/role-assignments/{assignment_id}`**.

```bash
curl -sS -X PATCH \
  'http://127.0.0.1:8080/v1/workspaces/0ac682f5-aee3-4968-9d21-692eb3fd4056/role-assignments/0218b8c4-f5a2-4a1e-bbbd-a986dd8aeb81' \
  -H 'Content-Type: application/json' \
  -d '{
    "role": "Contributor",
    "ticket_id": "CHG99999",
    "correlation_id": null
  }'
```

### Create a SQL connection (`POST /v1/connections/sql`)

You must send **exactly one** of **`basic`** or **`service_principal`** for credentials **to the SQL endpoint**. Example with SQL login:

```bash
curl -sS -X POST 'http://127.0.0.1:8080/v1/connections/sql' \
  -H 'Content-Type: application/json' \
  -d '{
    "display_name": "Warehouse link",
    "server": "x.datawarehouse.pbidedicated.windows.net",
    "database": "MyWarehouse",
    "basic": { "username": "sql_reader", "password": "use-secret-store-in-prod" },
    "grants": [
      {
        "object_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "principal_type": "Group",
        "role": "User"
      }
    ],
    "ticket_id": "CHG1",
    "skip_test_connection": false
  }'
```

---

## 5. Webhook integration

If **`INTEGRATION_WEBHOOK_URL`** is set, a successful **workspace** or **SQL connection** run **POST**s JSON to that URL (payload shapes are described in the [root README](https://github.com/calvinchengx/fabric/blob/main/README.md#configuration)). **Role assignment updates** (`update-workspace-role` / `PATCH` role assignments) do not trigger that webhook in the current code—they are still recorded on **stdout** and optional **JSONL** audit.

---

## 6. See also

| Topic | Document |
|-------|----------|
| Minimal install → first `just health` | [get-started.md](get-started.md) |
| Entra vs Fabric, API list, tenant settings | [architecture.md](architecture.md) |
| Who may run the tool, change control, security checklist | [governance.md](governance.md) |
| Full variable list, tests, license | [repository.md](repository.md) → [root README](https://github.com/calvinchengx/fabric/blob/main/README.md) |

CLI entrypoint (**Typer**): **`fabric-provision`**, wrapped here as **`just cli …`** (see **`justfile`**).
