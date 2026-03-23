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

## Pull requests

- Keep changes focused on one concern when possible.
- Describe what changed and why in the PR body.
- For security-sensitive issues, see **[SECURITY.md](SECURITY.md)** instead of filing a public issue with exploit details.

Design and API background: **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**. Operational expectations: **[docs/GOVERNANCE.md](docs/GOVERNANCE.md)**.
