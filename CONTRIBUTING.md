# Contributing

Thanks for helping improve **fabric-provisioner**. This project is **Python 3.11+** and uses **[uv](https://docs.astral.sh/uv/)** for environments and dependencies.

## Setup

From the repository root:

```bash
uv sync --all-groups
cp .env.example .env   # optional; needed for live Fabric / Entra calls
```

Use the interpreter at **`.venv`** in your editor so imports and Pyright match `pyproject.toml`.

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

## Documentation site (MkDocs)

```bash
uv sync --group docs
uv run mkdocs serve    # http://127.0.0.1:8000
uv run mkdocs build --strict
```

CI deploys to **GitHub Pages** when **`docs/`** or **`mkdocs.yml`** changes on the default branch. If links in **`docs/`** point outside that folder, use full **GitHub** URLs (see **`docs/repository.md`**) so **`mkdocs build --strict`** passes.

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

Documentation index (Fabric scope): **[docs/README.md](docs/README.md)**. Design and API background: **[docs/architecture.md](docs/architecture.md)**. Operational expectations: **[docs/governance.md](docs/governance.md)**.
