import gzip
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from fabric_provisioner.api import app
from fabric_provisioner.config import Settings
from fabric_provisioner.inventory.core_collect import (
    CoreInventoryOptions,
    InventoryDisabledError,
    _collect_all_pages,
    collect_core_inventory,
    run_core_inventory_pipeline,
)
from fabric_provisioner.inventory.output import write_manifest_json
from fabric_provisioner.inventory.schema import MANIFEST_VERSION, build_full_manifest


def test_collect_all_pages_follows_continuation_token() -> None:
    tokens_seen: list[str | None] = []

    def fetch_page(token: str | None) -> dict:
        tokens_seen.append(token)
        if token is None:
            return {"value": [{"a": 1}], "continuationToken": "next"}
        if token == "next":
            return {"value": [{"b": 2}], "continuationToken": None}
        msg = f"unexpected token {token!r}"
        raise AssertionError(msg)

    rows = _collect_all_pages(fetch_page)
    assert tokens_seen == [None, "next"]
    assert rows == [{"a": 1}, {"b": 2}]


def test_collect_core_inventory_one_workspace_items_and_roles() -> None:
    settings = Settings(
        azure_tenant_id="tenant-1",
        azure_client_id="c",
        azure_client_secret="s",
        validate_group_ids_with_graph=False,
    )
    fabric = MagicMock()
    fabric.list_workspaces_page.return_value = {
        "value": [{"id": "ws-1", "displayName": "Demo"}],
        "continuationToken": None,
    }
    fabric.list_workspace_items_page.return_value = {
        "value": [{"id": "it-1", "displayName": "Lakehouse"}],
        "continuationToken": None,
    }
    fabric.list_workspace_role_assignments_page.return_value = {
        "value": [{"id": "ra-1", "principal": {"id": "u1"}}],
        "continuationToken": None,
    }

    core = collect_core_inventory(
        settings,
        fabric,
        options=CoreInventoryOptions(),
        audit=None,
    )

    assert core["source"] == "fabric_core"
    assert core["summary"]["workspace_count"] == 1
    assert core["summary"]["item_count"] == 1
    assert core["summary"]["role_assignment_count"] == 1
    assert len(core["workspaces"]) == 1
    wid = core["workspaces"][0]["workspace"]["id"]
    assert wid == "ws-1"
    assert len(core["workspaces"][0]["items"]) == 1
    assert len(core["workspaces"][0]["role_assignments"]) == 1
    assert core["partial_errors"] == []


def test_collect_core_inventory_multi_page_workspaces() -> None:
    settings = Settings(
        azure_tenant_id="t",
        azure_client_id="c",
        azure_client_secret="s",
        validate_group_ids_with_graph=False,
    )
    fabric = MagicMock()
    fabric.list_workspaces_page.side_effect = [
        {"value": [{"id": "w1", "displayName": "A"}], "continuationToken": "t2"},
        {"value": [{"id": "w2", "displayName": "B"}], "continuationToken": None},
    ]
    fabric.list_workspace_items_page.return_value = {
        "value": [],
        "continuationToken": None,
    }
    fabric.list_workspace_role_assignments_page.return_value = {
        "value": [],
        "continuationToken": None,
    }

    core = collect_core_inventory(settings, fabric, audit=None)

    assert core["summary"]["workspace_count"] == 2
    assert fabric.list_workspaces_page.call_count == 2


def test_collect_core_inventory_records_partial_item_errors() -> None:
    settings = Settings(
        azure_tenant_id="t",
        azure_client_id="c",
        azure_client_secret="s",
        validate_group_ids_with_graph=False,
    )
    fabric = MagicMock()
    fabric.list_workspaces_page.return_value = {
        "value": [{"id": "ws-bad", "displayName": "X"}],
        "continuationToken": None,
    }
    fabric.list_workspace_items_page.side_effect = RuntimeError("items failed")
    fabric.list_workspace_role_assignments_page.return_value = {
        "value": [],
        "continuationToken": None,
    }

    core = collect_core_inventory(settings, fabric, audit=None)

    assert core["partial_errors"]
    assert core["partial_errors"][0]["scope"] == "items"
    assert core["partial_errors"][0]["workspace_id"] == "ws-bad"
    assert core["workspaces"][0]["items"] == []


def test_build_full_manifest_top_level_fields() -> None:
    m = build_full_manifest(
        tenant_id="tid",
        core={"summary": {"workspace_count": 0}},
        admin_scan=None,
        errors=[{"scope": "admin_scan", "code": "not_implemented"}],
        correlation_id="corr",
        ticket_id="T1",
    )
    assert m["manifest_version"] == MANIFEST_VERSION
    assert m["tenant_id"] == "tid"
    assert m["correlation_id"] == "corr"
    assert m["ticket_id"] == "T1"
    assert m["core"]["summary"]["workspace_count"] == 0
    assert m["admin_scan"] is None
    assert len(m["errors"]) == 1


def test_run_core_inventory_pipeline_raises_when_disabled() -> None:
    settings = Settings(
        azure_tenant_id="t",
        azure_client_id="c",
        azure_client_secret="s",
        validate_group_ids_with_graph=False,
        inventory_enabled=False,
    )
    with pytest.raises(InventoryDisabledError):
        run_core_inventory_pipeline(settings, options=CoreInventoryOptions())


def test_run_core_inventory_pipeline_allowlist_intersection() -> None:
    allow = "11111111-1111-1111-1111-111111111111"
    settings = Settings(
        azure_tenant_id="t",
        azure_client_id="c",
        azure_client_secret="s",
        validate_group_ids_with_graph=False,
        inventory_workspace_allowlist=allow,
    )
    fabric = MagicMock()
    fabric.list_workspaces_page.return_value = {
        "value": [{"id": allow, "displayName": "Only"}],
        "continuationToken": None,
    }
    fabric.list_workspace_items_page.return_value = {"value": [], "continuationToken": None}
    fabric.list_workspace_role_assignments_page.return_value = {
        "value": [],
        "continuationToken": None,
    }
    fabric.__enter__ = MagicMock(return_value=fabric)
    fabric.__exit__ = MagicMock(return_value=False)
    with (
        patch(
            "fabric_provisioner.inventory.core_collect.acquire_client_credentials_token",
            return_value="tok",
        ),
        patch(
            "fabric_provisioner.inventory.core_collect.FabricClient",
            return_value=fabric,
        ),
    ):
        run_core_inventory_pipeline(
            settings,
            options=CoreInventoryOptions(workspace_ids=frozenset({allow})),
            audit=None,
        )
    fabric.list_workspaces_page.assert_called()


def test_run_core_inventory_pipeline_allowlist_rejects_unknown_workspace() -> None:
    settings = Settings(
        azure_tenant_id="t",
        azure_client_id="c",
        azure_client_secret="s",
        validate_group_ids_with_graph=False,
        inventory_workspace_allowlist="11111111-1111-1111-1111-111111111111",
    )
    with pytest.raises(ValueError, match="FABRIC_INVENTORY_WORKSPACE_ALLOWLIST"):
        run_core_inventory_pipeline(
            settings,
            options=CoreInventoryOptions(
                workspace_ids=frozenset({"22222222-2222-2222-2222-222222222222"}),
            ),
            audit=None,
        )


def test_write_manifest_json_roundtrip_plain_and_gzip(tmp_path: Path) -> None:
    manifest = {"manifest_version": "1", "x": 1}
    plain = tmp_path / "m.json"
    write_manifest_json(plain, manifest, gzip_compress=False)
    assert json.loads(plain.read_text(encoding="utf-8")) == manifest
    gz_path = tmp_path / "m.json.gz"
    write_manifest_json(gz_path, manifest, gzip_compress=True)
    with gzip.open(gz_path, "rb") as zf:
        assert json.loads(zf.read().decode("utf-8")) == manifest


def test_post_inventory_core_ok() -> None:
    settings = Settings(
        azure_tenant_id="t",
        azure_client_id="c",
        azure_client_secret="s",
        validate_group_ids_with_graph=False,
    )
    stub = {
        "manifest_version": MANIFEST_VERSION,
        "tenant_id": "t",
        "core": {"summary": {"workspace_count": 0}},
        "errors": [],
    }
    with (
        patch("fabric_provisioner.api.get_settings", return_value=settings),
        patch("fabric_provisioner.api.run_core_manifest_only", return_value=stub),
    ):
        client = TestClient(app)
        resp = client.post("/v1/inventory/core", json={})

    assert resp.status_code == 200
    assert resp.json()["manifest_version"] == MANIFEST_VERSION


def test_post_inventory_core_forbidden_when_disabled() -> None:
    settings = Settings(
        azure_tenant_id="t",
        azure_client_id="c",
        azure_client_secret="s",
        validate_group_ids_with_graph=False,
        inventory_enabled=False,
    )
    with patch("fabric_provisioner.api.get_settings", return_value=settings):
        client = TestClient(app)
        resp = client.post("/v1/inventory/core", json={})
    assert resp.status_code == 403


def test_post_inventory_core_allowlist_mismatch_is_400() -> None:
    settings = Settings(
        azure_tenant_id="t",
        azure_client_id="c",
        azure_client_secret="s",
        validate_group_ids_with_graph=False,
        inventory_workspace_allowlist="11111111-1111-1111-1111-111111111111",
    )
    with patch("fabric_provisioner.api.get_settings", return_value=settings):
        client = TestClient(app)
        resp = client.post(
            "/v1/inventory/core",
            json={"workspace_ids": ["22222222-2222-2222-2222-222222222222"]},
        )
    assert resp.status_code == 400


def test_post_inventory_full_merges_admin_stub_error() -> None:
    settings = Settings(
        azure_tenant_id="t",
        azure_client_id="c",
        azure_client_secret="s",
        validate_group_ids_with_graph=False,
    )
    stub = build_full_manifest(
        tenant_id="t",
        core={"summary": {"workspace_count": 0}},
        admin_scan=None,
        errors=[{"scope": "admin_scan", "code": "not_implemented", "message": "stub"}],
    )
    with (
        patch("fabric_provisioner.api.get_settings", return_value=settings),
        patch("fabric_provisioner.api.run_full_inventory_pipeline", return_value=stub),
    ):
        client = TestClient(app)
        resp = client.post("/v1/inventory/full", json={})

    assert resp.status_code == 200
    body = resp.json()
    assert body["errors"] and body["errors"][0].get("code") == "not_implemented"
