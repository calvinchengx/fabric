# Governance, operations, and security

This document states **how we expect** the platform team and workspace owners to **govern**, **operate**, and **secure** Microsoft Fabric in conjunction with this repo. It complements [ARCHITECTURE.md](ARCHITECTURE.md) (technical split between Entra and the thin provisioner).

## Governance (who decides access)

### Entra is the policy system of record

- **Workspace access for people** is expressed with **Entra security groups** mapped to Fabric workspace roles (Admin, Member, Contributor, Viewer). Membership changes happen in **Entra** (manual, dynamic groups, or **Access Packages** / lifecycle), not by ad-hoc sharing of admin accounts.
- **Joiner / mover / leaver** is handled with standard Entra processes. Removing a user from the right groups (or disabling the account) **revokes** Fabric access that was granted through those groups.
- **Access reviews** and **privileged roles** (where used) follow your org’s IAM standards; this Python service **does not** replace Entitlement Management, PIM, or catalog approvals.

### Roles and accountability

- **Fabric / tenant administrators** are **named individuals** with a documented role — not a shared “root” login for day-to-day work. Use **break-glass** accounts only for emergencies, with **strong monitoring**.
- **Workspace admins** own **who** is in their workspace (often via **which groups** are assigned). They do not bypass Entra policy by sharing credentials.
- **Automation** is performed by **service principals (SPNs)** that are **owned**, **named**, and **scoped** (one app registration per distinct automation identity in the tenant, each with its own credential material in a vault).

### What we avoid

- **No shared root / shared admin** for building pipelines, notebooks, or provisioning. That destroys **auditability** (every action looks like one identity), blows up **blast radius**, and breaks **offboarding**.
- **No long-lived secrets in git** or chat. Client secrets and certificates live in **Azure Key Vault** (or equivalent) and are injected at runtime.

## Operations (how we run the provisioner and workspaces)

### Running `fabric-provisioner`

- **Who may invoke it:** only **approved automation** (CI/CD, scheduled job, internal API behind auth) or **named operators** with a ticket. Prefer **one provisioner SPN per environment** (e.g. dev / test / prod) with **separate** `AZURE_CLIENT_ID` / secret injection — not one mega-credential for everything.
- **Change control:** workspace **creation** and **default group assignments** should tie to a **catalog or change record** (`ticket_id`, `correlation_id`) so operations can explain *why* a workspace exists.
- **Environments:** non-prod and prod **Fabric capacities / domains** are separated where the business requires it; provisioner config (e.g. `capacity_id`) reflects that separation.

### Workspace lifecycle

- **Create:** via this tool or an approved process that calls the same APIs; record **display name**, **owning team**, and **default groups** in your CMDB or service catalog if required.
- **Modify access:** prefer **Entra group** changes; use API-only group assignment changes when automation must align a new workspace with a **frozen** default pattern.
- **Decommission:** disable or delete workspace per org process; **rotate or remove** SPN role assignments and connection credentials that pointed at that workspace.

### Audit vs execution identity (for investigators)

- **Authoring** (who saved a notebook or pipeline) is usually attributed to the **signed-in user**.
- **Execution** (scheduled refresh, connection using stored SPN credentials, API calls) is attributed to **whichever identity obtained the token** for that run — often the **SPN** or the **connection credential**, not the person who last edited the artifact.
- Operational runbooks should document **which connections use SPN vs OAuth user** so audit interpretation is correct.

## Security (controls we expect)

### Entra app registrations used by this repo

- **Dedicated app** for the provisioner (not shared with unrelated products) unless your security team explicitly approves reuse.
- **Least privilege** on **Fabric** and **Graph**: grant only what Create Workspace, role assignment, and optional `Group.Read.All` (or narrower) validation require — per Microsoft Learn and your tenant’s admin consent process.
- **Credential type:** prefer **certificate** over client secret where your platform supports it; **rotate** on a schedule.

### Fabric tenant settings

- **Service principals can use Fabric APIs** / **can create workspaces** (and related options) are scoped using **security groups** where possible — not “entire organization” unless policy explicitly allows.
- Review Microsoft’s current guidance in the [Fabric admin portal — Developer settings](https://learn.microsoft.com/en-us/fabric/admin/service-admin-portal-developer).

### Secrets and runtime

- Provisioner reads `AZURE_CLIENT_SECRET` from **environment** or secret store integration — **never** commit `.env` or real secrets to this repository.
- If the **HTTP API** is deployed, place it **behind** your org’s gateway (mTLS, OAuth, private network, IP allow lists) so anonymous callers cannot create workspaces.

### Logging and monitoring

- Enable **stdout / JSONL** audit fields from this app (`AUDIT_JSONL_PATH`, structured lines) and forward them to your **SIEM**. Use **`fabric-provision audit-dump`** to stream the JSONL file to stdout for one-off exports or pipelines (see [README.md](../README.md#logs-and-extraction)).
- Record **correlation_id** and **ticket_id** on every provision so security and operations can trace **caller → change**.
- **Tenant-wide Fabric / Power BI activity** (beyond this provisioner) comes from **Microsoft audit / Purview** and related exports — not from this package; ingest those separately into the same SIEM if you want combined reporting.
- Monitor **Graph and Fabric sign-in / audit** exports per Microsoft documentation for your compliance regime.

### Incident response

- **Compromise of the provisioner SPN:** revoke secret/cert, review workspaces and role assignments created in the exposure window, rotate credentials, tighten tenant settings.
- **Compromise of a workspace automation SPN:** treat like any application credential — remove workspace access, rotate, root-cause how the secret leaked.

## Summary checklist

| Area | Expectation |
|------|-------------|
| People access | Entra **groups** on workspaces; lifecycle in Entra |
| Admin access | **Named** admins; break-glass rare and monitored |
| Automation | **Dedicated SPNs**; secrets in **vault**; tenant settings **scoped** |
| This app | **Least privilege**; audit fields; no secrets in git |
| Audit | Distinguish **author** vs **run-as / connection** identity |

For technical API details and repo layout, see [ARCHITECTURE.md](ARCHITECTURE.md).
