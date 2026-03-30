# Fabric Core tenant inventory (manifest v1)

`fabric-provisioner` can crawl **Microsoft Fabric Core REST** (`api.fabric.microsoft.com`) and emit a single JSON **manifest** with a stable top-level shape. This path lists **workspaces**, optional **items** per workspace, and optional **workspace role assignments**, using the same pagination model as the product APIs (`continuationToken`).

This is **not** a replacement for Microsoft Power BI / Fabric **admin** or **Scanner** APIs. A separate **Phase B** flow may add `admin_scan` later; until then, **`inventory full`** and `POST /v1/inventory/full` still return Core data plus a documented `errors` entry for the unimplemented admin leg.

## Permissions

Core inventory needs an app registration that can call Fabric Core read APIs (for example **list workspaces**, **list items**, **list workspace role assignments**). Map Microsoft Learn’s delegated permission names to **application** permissions for client credentials as appropriate for your tenant, and ensure the service principal is allowed to use Fabric in **tenant settings** (developer / API access policies your org uses).

Authoritative links are embedded in manifest output under `core.documentation` for traceability.

## How to run

- **CLI** (after configuring `.env` like the rest of the tool):
  - **`just inventory-core`** — Core crawl only (same as `just cli inventory core`).
  - **`just inventory-full`** — Core plus admin placeholder / `errors` merge (`just cli inventory full`).
  - **File output:** `-o` / `--output` writes compact JSON; `--gzip` compresses the file; **`--no-stdout`** skips printing (useful for large tenants). Example: **`just inventory-core -- --max-workspaces 1 -o ./manifest.json`** (use **`--`** before flags so **just** does not swallow them).
  - **Without just:** from the repo root, **`uv run fabric-provision inventory core`** (or **`inventory full`**) after **`uv sync`**.
- **HTTP** (when the API server is running):
  - `POST /v1/inventory/core` — body: optional filters (`include_items`, `workspace_ids`, `max_workspaces`, …). See `InventoryCoreRequest` in `models.py`.
  - `POST /v1/inventory/full` — same body; merges Phase B stub.

## Manifest shape (v1)

Top-level keys include:

- `manifest_version` — `"1"`
- `generated_at` — UTC ISO timestamp
- `tenant_id` — Entra tenant from configuration
- `correlation_id`, `ticket_id` — optional passthrough from request
- `core` — Fabric Core crawl (workspaces, items, role assignments, summaries, `partial_errors` for per-workspace failures)
- `admin_scan` — optional; `null` until Phase B
- `errors` — top-level issues (e.g. admin not implemented on `inventory full`)

Treat full manifests as **sensitive metadata**; restrict storage and access like any tenant inventory export.

## Configuration

- **`FABRIC_INVENTORY_ENABLED`** — default `true`. Set to `false` to turn off inventory CLI and HTTP routes (**403** from the API).
- **`FABRIC_INVENTORY_WORKSPACE_ALLOWLIST`** — optional comma-separated workspace UUIDs. When set, every inventory run is restricted to that set (intersected with `--workspace-id` / API `workspace_ids`). Empty intersection yields **400** / CLI error.

## Operational notes

- Large tenants: responses can be large; prefer scheduled jobs, file sinks, or HTTP clients with adequate timeouts.
- **429** responses from Fabric are retried when the API returns **Retry-After** (see `FabricClient`).

For provisioning workspaces and SQL connections, see [usage.md](usage.md) and [permissions.md](permissions.md).
