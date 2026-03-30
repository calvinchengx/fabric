# Shortcuts for fabric-provisioner (requires uv on PATH).
# Install just: https://github.com/casey/just#installation
# List recipes: `just` or `just --list`

default:
    @just --list

# Install all dependency groups (app + dev + docs)
sync:
    uv sync --all-groups

# --- Tool ---
health:
    uv run fabric-provision health

# Pass any CLI subcommand and flags, e.g. `just cli create-workspace --help`
cli *args:
    uv run fabric-provision {{args}}

# Tenant inventory (manifest v1); pass flags after recipe name, e.g. `just inventory-core -- --max-workspaces 1`
inventory-core *args:
    uv run fabric-provision inventory core {{args}}

inventory-full *args:
    uv run fabric-provision inventory full {{args}}

# HTTP API (default http://127.0.0.1:8080 — override: `just api 3000`)
api port="8080":
    uv run uvicorn fabric_provisioner.api:app --host 127.0.0.1 --port {{port}}

# --- Documentation ---
docs:
    uv sync --group docs
    uv run mkdocs serve

docs-build:
    uv sync --group docs
    uv run mkdocs build

docs-strict:
    uv sync --group docs
    uv run mkdocs build --strict

# --- CI-style checks ---
test:
    uv run pytest

lint:
    uv run ruff check src tests
