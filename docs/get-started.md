# Get started

This is the **shortest path** from zero to a working **fabric-provisioner** install: dependencies, configuration, and a first command that proves Entra + Fabric are set up correctly.

**Next:** [usage.md](usage.md) — full CLI, HTTP, and `curl` examples · [permissions.md](permissions.md) — what your tenant must grant · [architecture.md](architecture.md) — how the pieces fit together.

---

## What you need

| Prerequisite | Notes |
|--------------|------|
| **Python 3.11+** | The project targets 3.11+; 3.12/3.13 are fine. |
| **[uv](https://docs.astral.sh/uv/)** | Installs the app and dev/docs dependencies into **`.venv`**. |
| **[just](https://github.com/casey/just)** (recommended) | Short commands from **`justfile`**; optional — see [usage.md](usage.md) for **`uv run …`** equivalents. |
| **Microsoft Entra app registration** | Client ID + client secret (or adapt the code for certificates). Used for **OAuth client credentials** only — no interactive login in this package. |
| **Tenant configuration** | A **Fabric administrator** must allow your service principal to **use Fabric APIs** (and to **create workspaces** / **connections** if you plan to use those features). See [permissions.md](permissions.md) and **Tenant prerequisites** in [architecture.md](architecture.md#apis-in-use). |

### Is the provisioner an Entra app registration?

**The Python project is not registered** — it is just code you run. What **is** registered is the **Microsoft Entra application (app registration)** whose **client ID** and **secret** you put in **`.env`**. That registration represents the **provisioner’s identity** (a **service principal** in your tenant) when the tool uses **OAuth client credentials**.

So in **plain language**: you are **not** turning this Git repo into an Entra object. But **yes** — for Identity and Fabric, **the thing that is allowed to automate work is an Entra app registration** (its service principal). People often say *“fabric-provisioner is our Entra application”* and mean **that registration**, not the Python package.

**Where to register it** (your organization’s tenant only):

1. **[Microsoft Entra admin center](https://entra.microsoft.com)** → **Applications** → **App registrations** → **New registration**  
   — or **[Azure portal](https://portal.azure.com)** → **Microsoft Entra ID** → **App registrations** → **New registration**.
2. Choose a name (for example `fabric-provisioner-prod`), account type (usually **single tenant**), then create the app.
3. From **Overview**, copy the **Application (client) ID** → **`AZURE_CLIENT_ID`** and **Directory (tenant) ID** → **`AZURE_TENANT_ID`**.
4. Under **Certificates & secrets**, create a **client secret** → **`AZURE_CLIENT_SECRET`** (store it in a vault for anything beyond local dev).

Then your **Identity / IAM** team (or Entra admins) attach the **API permissions** and **admin consent** this app needs for Fabric (and optionally Graph), and a **Fabric administrator** allows this app’s **service principal** in **Fabric tenant settings**. Details: [permissions.md](permissions.md). Microsoft’s overview: [Register an application](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app).

---

## 1. Clone and install

From the **repository root** (where **`pyproject.toml`** and **`justfile`** live):

```bash
git clone https://github.com/calvinchengx/fabric.git
cd fabric
just sync
```

Without **just:** `uv sync --all-groups`.

---

## 2. Configure credentials

```bash
cp .env.example .env
```

Edit **`.env`** and set at least (all from the **same app registration** above):

- **`AZURE_TENANT_ID`** — Directory (tenant) ID of your Entra tenant  
- **`AZURE_CLIENT_ID`** — Application (client) ID of the provisioner app registration  
- **`AZURE_CLIENT_SECRET`** — Client secret you created on that app registration  

All optional variables are described in **`.env.example`** and the [configuration table in the root README](https://github.com/calvinchengx/fabric/blob/main/README.md#configuration).

**Editors:** choose the **`.venv`** interpreter after sync so your IDE resolves imports.

---

## 3. Verify Fabric authentication

This acquires a Fabric-scoped token. It does **not** create a workspace or change anything in Fabric.

```bash
just health
```

You should see an **ok** message. If you get an error, fix **`.env`**, app registration permissions, and [Fabric developer settings](https://learn.microsoft.com/en-us/fabric/admin/service-admin-portal-developer) before continuing — see [permissions.md](permissions.md).

---

## 4. What to run next

| Goal | Where to go |
|------|-------------|
| Create a workspace, SQL connections, role updates, **`curl`**, audit | **[usage.md](usage.md)** |
| Entra app permissions vs workspace **Admin**, least privilege | **[permissions.md](permissions.md)** |
| APIs used, tenant prerequisites, repo layout | **[architecture.md](architecture.md)** |
| Operations, checklists, who may run the tool | **[governance.md](governance.md)** |

**HTTP API locally:** `just api` then open **http://127.0.0.1:8080/docs** (Swagger). **Browse this documentation** in MkDocs: `just docs` (usually **http://127.0.0.1:8000**).

**Contributors:** tests, lint, **`justfile`** reference — **[CONTRIBUTING.md](https://github.com/calvinchengx/fabric/blob/main/CONTRIBUTING.md)**.

---

## Troubleshooting (quick)

- **`just` not found:** install [just](https://github.com/casey/just#installation) or use **`uv run fabric-provision …`** (see [usage.md](usage.md)).
- **Token / auth errors on `just health`:** confirm secrets, that admin consent was granted for Fabric (and Graph if you validate IDs), and that the service principal is allowed to use Fabric APIs in the **admin portal**.
- **“Insufficient permissions” on create workspace / connections:** compare your app’s permissions and portal toggles with each API’s **Permissions** on [Microsoft Learn](https://learn.microsoft.com/en-us/rest/api/fabric/core/workspaces/create-workspace) and [permissions.md](permissions.md).
