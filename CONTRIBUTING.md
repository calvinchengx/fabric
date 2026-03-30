# Contributing

Thanks for helping improve **fabric-provisioner**. This project is **Python 3.11+** and uses **[uv](https://docs.astral.sh/uv/)** for environments and dependencies.

## Setup

From the repository root:

```bash
uv sync --all-groups
cp .env.example .env   # optional; needed for live Fabric / Entra calls
```

Use the interpreter at **`.venv`** in your editor so imports and Pyright match `pyproject.toml`.

## Short commands with just

**Recommendation:** install **[just](https://github.com/casey/just)** — a single command runner that works the same on **Windows**, **Linux**, and **macOS**. Full package list and edge cases: **[just — Installation](https://github.com/casey/just#installation)**.

### Installing just

**Windows**

- **winget:** `winget install --id Casey.Just -e`
- **Chocolatey:** `choco install just` (run from an elevated shell if your org requires it)
- **Scoop:** `scoop install just`
- Or download a release binary from the **[just Releases](https://github.com/casey/just/releases)** page and put it on your `PATH`.

**Linux**

- **Arch:** `sudo pacman -S just`
- **Fedora:** `sudo dnf install just`
- **Debian / Ubuntu** (and derivatives): some releases ship **`just`** in the distro repos; otherwise use **`cargo install just`**, a **[release binary](https://github.com/casey/just/releases)**, or follow **[upstream install steps](https://github.com/casey/just#installation)**.
- **Cargo** (Rust toolchain installed): `cargo install just`

**macOS**

- **Homebrew:** `brew install just`
- **MacPorts:** `sudo port install just`
- **Cargo:** `cargo install just`

Verify: **`just --version`**. Then from this repository’s root:

| Goal | Command |
|------|---------|
| List recipes | `just` |
| Sync deps (all groups) | `just sync` |
| Fabric token smoke test | `just health` |
| Any CLI subcommand | `just cli create-workspace --help`, `just cli health`, … |
| HTTP API (port 8080) | `just api` — or `just api 3000` |
| MkDocs live site | `just docs` |
| MkDocs build / strict | `just docs-build`, `just docs-strict` |
| Tests / Ruff | `just test`, `just lint` |

Recipes live in **`justfile`** at the repository root. They still invoke **`uv run`**, so you keep one toolchain (**uv** + **just**).

**Without just:** use the same **`uv run …`** commands as in the sections below (or add shell aliases if you prefer zero extra installs).

## Running the tool

You need a filled **`.env`** (copy from **`.env.example`**) for any command that talks to **Entra** or **Fabric** (`AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`).

### CLI

Entry point: **`fabric-provision`** (Typer).

```bash
uv run fabric-provision --help
uv run fabric-provision create-workspace --help
```

Smoke-check Fabric token acquisition (no workspace changes):

```bash
uv run fabric-provision health
```

**Copy-paste examples** (workspace, SQL connection, role update, audit): **[`docs/usage.md`](docs/usage.md)**.

### HTTP API

```bash
uv run uvicorn fabric_provisioner.api:app --host 127.0.0.1 --port 8080
```

- **Liveness:** `GET http://127.0.0.1:8080/healthz` (does not call Fabric).  
- **OpenAPI:** `http://127.0.0.1:8080/docs` (Swagger) or **`/redoc`**.  

Same **`.env`** as the CLI; example `curl` bodies are in **`docs/usage.md`**.

## Tests

```bash
uv run pytest
```

Add or update tests under **`tests/`** when you change behavior users rely on.

## Lint

```bash
uv run ruff check src tests
```

Fix issues before opening a PR when practical.

## Running the documentation (MkDocs)

Markdown under **`docs/`** is readable **on GitHub** as-is. To build the **static site** (Material theme, search, nav from **`mkdocs.yml`**):

```bash
uv sync --group docs          # or: uv sync --all-groups (includes docs)
uv run mkdocs serve           # live reload — usually http://127.0.0.1:8000
uv run mkdocs build           # output in ./site/
uv run mkdocs build --strict  # stricter link checks (CI-friendly)
```

**Nav** is defined in **[`mkdocs.yml`](mkdocs.yml)** (Home → Usage → Architecture → Governance → Project README). **Hands-on tool examples** live in **[`docs/usage.md`](docs/usage.md)**.

CI deploys to **GitHub Pages** when **`docs/`** or **`mkdocs.yml`** changes on the default branch (see **[`.github/workflows/docs.yml`](.github/workflows/docs.yml)**). If links in **`docs/`** point outside that folder, use full **GitHub** URLs (see **`docs/repository.md`**) so **`mkdocs build --strict`** passes when you enable it in automation.

## CI and GitHub Releases

**Continuous integration** ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs on pushes and pull requests to **`main`** / **`master`**: **Ruff**, **pytest** on Python **3.11–3.13**, and a **`uv build`** smoke check.

**Releases** ([`.github/workflows/release.yml`](.github/workflows/release.yml)) run when you push a version tag **`v*`** (for example **`v0.2.0`**). The workflow re-runs the same checks, builds **sdist + wheel** with **`uv build`**, and creates a **GitHub Release** with those files attached (auto-generated release notes from merged PRs).

Typical release steps:

1. Set **`version`** in **[`pyproject.toml`](pyproject.toml)** to match the tag (e.g. **`0.2.0`** for tag **`v0.2.0`**).
2. Commit and push to **`main`**.
3. Create and push the tag: **`git tag v0.2.0 && git push origin v0.2.0`**

To publish to **PyPI** as well, add a **`PYPI_API_TOKEN`** repository secret and a **`uv publish`** step (or **Trusted Publishing**); this repo currently only attaches artifacts to GitHub Releases.

## Pull requests

- Keep changes focused on one concern when possible.
- Describe what changed and why in the PR body.
- For security-sensitive issues, see **[SECURITY.md](SECURITY.md)** instead of filing a public issue with exploit details.

Documentation index (Fabric scope): **[docs/README.md](docs/README.md)**. **Get started:** **[docs/get-started.md](docs/get-started.md)**. **How to run the tool:** **[docs/usage.md](docs/usage.md)**. **Permissions / least privilege:** **[docs/permissions.md](docs/permissions.md)**. Design and API background: **[docs/architecture.md](docs/architecture.md)**. Operational expectations: **[docs/governance.md](docs/governance.md)**.
