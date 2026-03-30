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

## Pull requests

- Keep changes focused on one concern when possible.
- Describe what changed and why in the PR body.
- For security-sensitive issues, see **[SECURITY.md](SECURITY.md)** instead of filing a public issue with exploit details.

Documentation index (Fabric scope): **[docs/README.md](docs/README.md)**. Design and API background: **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**. Operational expectations: **[docs/GOVERNANCE.md](docs/GOVERNANCE.md)**.
