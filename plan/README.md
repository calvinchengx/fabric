# Fabric tenant manifest — implementation plan (Option A)

This document describes how to add **both** a **Fabric Core–centric** inventory and an **admin / scanner–centric** tenant snapshot **inside the same repository** as `fabric-provisioner` (**Option A**): shared auth, config, and conventions; separate permission profiles and clients where Microsoft splits API surfaces.

**Audience:** maintainers and security reviewers. This is a **plan**, not a commitment to every API URL or permission name—those must be pinned from [Microsoft Learn](https://learn.microsoft.com/en-us/rest/api/fabric/) at implementation time.

---

## 1. Product shape (Option A)

- **Location:** `src/fabric_provisioner/` gains an **`inventory`** (or `manifest`) submodule—e.g. `fabric_provisioner.inventory`—plus CLI entry points (Typer subcommands or top-level commands) and optional HTTP routes if you expose the job as a service.
- **Modes:** At least two user-visible operations, for example:
  - **`inventory core`** — assemble manifest from **`api.fabric.microsoft.com`** (list workspaces, list items per workspace, optional connections / role assignments as scoped in MVP).
  - **`inventory admin`** (or **`inventory scan`**) — run the **admin/scanner** flow your org approves (separate base URL, async job pattern if required by Microsoft).
- **Unified output:** One **JSON manifest document (v1)** with top-level sections, for example:
  - `manifest_version`, `generated_at`, `tenant_id`, `correlation_id` (optional)
  - `core` — result of the Core-centric crawl (your normalized structure)
  - `admin_scan` — result of the admin/scanner path (raw or normalized; note schema is Microsoft-driven)
  - `errors` — partial failures (e.g. Core succeeded, admin failed)
- **Shared infrastructure:** Reuse **`auth.py`** (extend with additional token requests if admin APIs use a different **resource/scope**), **`config.py`** / **`Settings`** for optional feature flags and paths, **`audit`** for emit events (e.g. `inventory.core.started`, `inventory.admin.completed`).

---

## 2. Security and organization (non-negotiables)

### 2.1 Two permission profiles

| Profile | Purpose | Typical Entra posture |
|---------|---------|------------------------|
| **Core inventory** | Read paths on Fabric Core | Application permissions + consent for **read/list** APIs you call; Fabric **developer** settings allow this SPN to use Fabric APIs. |
| **Admin / scanner** | Tenant-wide governance metadata | **Separate** app registration recommended; [Enable service principal authentication for admin APIs](https://learn.microsoft.com/en-us/fabric/admin/enable-service-principal-admin-apis); admin consent; security-group allowlisting in portal. |

Implement as **`AZURE_CLIENT_ID` / secret** pairs (or cert) loaded from env—e.g. `AZURE_ADMIN_CLIENT_ID` + `AZURE_ADMIN_CLIENT_SECRET` **or** a single app only if security explicitly accepts combined blast radius.

### 2.2 Operations

- Separate **secrets** per environment (dev/test/prod).
- **Runbook:** who may trigger **admin** scans, frequency, retention, and storage (blob vs local JSON).
- Treat large manifest outputs as **sensitive** (metadata can aid reconnaissance).

---

## 3. Phase A — Fabric Core–centric pipeline (MVP)

**Goal:** Deterministic, paginated crawl of Fabric Core resources; populate `core` in the manifest.

1. **API inventory** — Document exact operations from Learn: e.g. list workspaces, list items per workspace, optional list/get connections. Record **pagination** (`continuationToken` or equivalent) and **429 / Retry-After** behavior.
2. **`FabricClient` (or `inventory/core_client.py`)** — Add thin GET wrappers with pagination helpers; shared retry policy (configurable backoff).
3. **Orchestrator `collect_core_manifest()`** —  
   - Fetch all workspaces (paginate).  
   - For each workspace (with configurable **concurrency** and **rate** limits), fetch child resources you need.  
   - Optional filters: capacity id, domain id, name prefix, allowlist of workspace ids (for safe dev runs).
4. **Output** — Build the `core` object; support **stdout** and **file** path; optional **gzip** for large tenants.
5. **Tests** — Mock HTTP: empty tenant, single page, multi-page pagination, throttling, one workspace failure (partial error in `errors`).
6. **Documentation** — `docs/` page: required Core permissions, Fabric portal prerequisites, explicit statement that this is **not** a Microsoft Scanner replacement.

**Exit criterion:** CLI (or library) produces a stable **`core`** section in a lower environment on a schedule.

---

## 4. Phase B — Admin / scanner–centric pipeline

**Goal:** Governance-oriented snapshot; populate `admin_scan` (and merge with Core).

1. **Select exact Microsoft flow** — Confirm current Learn docs: Scanner API (or successor), token **authority/resource** (`api.powerbi.com` or as documented), sync vs async job, and response shape.
2. **`admin_scanner_client.py` (new)** — Separate from Core client: different **base URL**, error handling, and **async job** loop if applicable (submit → poll → download).
3. **Orchestrator `collect_admin_manifest()`** — Returns normalized or raw payload + metadata (`scan_id`, `completed_at`).
4. **Merge `build_full_manifest(core, admin, errors)`** — Single JSON document; tolerate **partial** success (record failures in `errors` without dropping successful sections).
5. **Tests** — Fixtures from **sanitized** sample responses; failure paths (auth denied, scan timeout).
6. **Documentation** — Runbook: **higher privilege**, approvals, who runs in prod.

**Exit criterion:** Scheduled admin job in a controlled environment with monitoring.

---

## 5. Phase C — Hardening and product fit

- **Rate limiting & backoff** — Unified policy; optional metrics hooks (429 counts, duration).
- **Diff / retention** — Optional hash of last manifest; diff output for CMDB or ticketing.
- **CLI & HTTP parity** — Match repo patterns: e.g. **`just cli inventory core`**, optional **`POST /v1/inventory/full`** behind your gateway.
- **Audit fields** — **`ticket_id`** / **`correlation_id`** on long-running jobs for governance alignment with [governance.md](../docs/GOVERNANCE.md).
- **Governance** — Enforce separate SPNs per environment; never share admin credentials with generic CI without review.

---

## 6. Suggested sequencing

| Band | Deliverable | Status |
|------|-------------|--------|
| **1** | Manifest schema **v1** draft; Core **list workspaces** + pagination spike | Done (code) |
| **2** | Core full walk (workspaces → items); CLI **`inventory core`**; tests | Done (code) |
| **3** | Admin/scanner spike in **dev**; Entra + portal checklist signed off | Not started |
| **4** | Admin job + **`inventory full`** merge; integration tests with mocks | Stub only (merge + errors; no real admin API) |
| **5** | Hardening (retry, limits, size caps, partial failure); ops + security sign-off | Partial (429 retry, partial errors, allowlist; no streaming/size caps) |

Core MVP can ship before admin if admin approvals lag.

---

## 7. Option A — repository layout (illustrative)

```text
src/fabric_provisioner/
  inventory/
    __init__.py
    schema.py          # manifest_version, build_full_manifest, validation
    core_collect.py    # orchestration: workspaces → items …
    admin_collect.py   # scanner / admin API orchestration
  fabric_client.py     # extend with list_* + pagination OR core-only helpers
  # optional: admin_client.py if you prefer not to overload FabricClient

  cli.py                # new Typer commands: inventory core | admin | full
  api.py                # optional: POST /v1/inventory/…
```

**Tests:** `tests/test_inventory_core.py`, `tests/test_inventory_admin.py`.

**Docs:** `docs/inventory.md` (or section in architecture) linking to this plan.

---

## 8. Risk register

| Risk | Mitigation |
|------|------------|
| API or permission renames | Pin Learn URLs in code comments; periodic smoke tests. |
| Tenant scale (memory / timeout) | Streaming writes, pagination-only loops, optional workspace allowlist in dev. |
| Admin API access denied | Separate runbook and SPN; never merge admin secrets into Core-only pipelines. |
| “Full” manifest expectations | Document **gaps** explicitly (what Core + scanner do **not** cover). |
| Compliance | Classify output; encrypt at rest; retention limits. |

---

## 9. Relation to current `fabric-provisioner`

- **Provisioning** (create workspace, connections, role assignments) stays as today.
- **Inventory** is **additive**: new commands and library entry points, minimal changes to existing provisioning paths unless you factor shared HTTP utilities.
- **`justfile`:** add recipes e.g. **`just cli inventory core`**, **`just cli inventory full`** when CLI exists.

---

## 10. Implementation checklist

Use this list to track **code** vs **organization** work. Checked items reflect the repository as of the last plan update.

### 10.1 Product shape (§1)

- [x] `fabric_provisioner.inventory` submodule (`schema`, `core_collect`, `admin_collect` stub)
- [x] CLI: `inventory core`, `inventory full` ([`cli.py`](../src/fabric_provisioner/cli.py))
- [x] HTTP: `POST /v1/inventory/core`, `POST /v1/inventory/full` ([`api.py`](../src/fabric_provisioner/api.py))
- [x] Unified manifest v1 (`manifest_version`, `core`, `admin_scan`, `errors`, audit-friendly ids)
- [ ] CLI: dedicated `inventory admin` / `inventory scan` (Phase B; today **`full`** carries stub only)
- [ ] Optional Core scope: **connections** list/get in `core` (not implemented)

### 10.2 Phase A — Core MVP (§3)

- [x] Documented Learn links & pagination in manifest `core.documentation`; `continuationToken` loops
- [x] `FabricClient` GET wrappers: list workspaces, items, role assignments + **429 / Retry-After** retries
- [x] Orchestrator: paginated workspaces → per-workspace items & role assignments; filters (capacity, domain, prefix, IDs)
- [x] Dev safety: **`FABRIC_INVENTORY_ENABLED`**, **`FABRIC_INVENTORY_WORKSPACE_ALLOWLIST`**
- [x] Output: Rich **stdout**; **`-o` / `--output`**; **`--gzip`**; **`--no-stdout`**
- [x] Partial failures recorded in `core.partial_errors`
- [x] Tests: [`test_inventory_core.py`](../tests/test_inventory_core.py), [`test_fabric_client.py`](../tests/test_fabric_client.py) (pagination, 429, allowlist, API 403/400)
- [x] Docs: [`docs/inventory.md`](../docs/inventory.md), linked from [`docs/README.md`](../docs/README.md)
- [x] `justfile`: **`just inventory-core`**, **`just inventory-full`**
- [ ] Per-workspace **concurrency** and explicit **rate** limits (not implemented)
- [ ] **Streaming** manifest write / strict **size caps** for very large tenants (§5 / Band 5)

### 10.3 Phase B — Admin / scanner (§4)

- [ ] Microsoft admin/scanner flow chosen and pinned (scope, async vs sync)
- [ ] `admin_scanner_client` (or equivalent) + separate token/settings for admin APIs
- [x] Manifest **merge** (`build_full_manifest`) and **`inventory full`** returning core + stub `errors`
- [ ] Replace `admin_collect` stub with real collector + metadata (`scan_id`, etc.)
- [ ] `tests/test_inventory_admin.py` and sanitized fixtures
- [ ] Docs: high-privilege **runbook** (who runs prod admin jobs)

### 10.4 Phase C — Hardening (§5)

- [x] Inventory **CLI & HTTP** parity; **`ticket_id`** / **`correlation_id`** on inventory requests
- [ ] Unified backoff **metrics** / observability (429 counts, durations)
- [ ] Optional manifest **hash / diff / retention** for CMDB or ticketing
- [ ] Org policy: separate **SPNs per environment**; CI secrets hygiene (§2)

### 10.5 Organization (outside or alongside code)

- [ ] Sign off manifest schema **v1** with consumers (CMDB, FinOps, security).
- [ ] **Core inventory** Entra app + Fabric permissions documented for operators.
- [ ] **Admin scanner** Entra app + Fabric/Power BI admin portal enablement.
- [ ] Operational **runbook**: who may run admin scans, frequency, retention, storage.

---

* Plan version: 1.1 — checklist aligned with Option A (single repo; Phase B and org items remain open).*
