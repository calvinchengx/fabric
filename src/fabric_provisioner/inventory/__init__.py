"""Fabric tenant manifest inventory (Fabric Core + future admin/scanner). See plan/README.md."""

from fabric_provisioner.inventory.admin_collect import collect_admin_inventory
from fabric_provisioner.inventory.core_collect import (
    CoreInventoryOptions,
    InventoryDisabledError,
    collect_core_inventory,
    run_core_inventory_pipeline,
    run_core_manifest_only,
    run_full_inventory_pipeline,
)
from fabric_provisioner.inventory.schema import MANIFEST_VERSION, build_full_manifest

__all__ = [
    "MANIFEST_VERSION",
    "CoreInventoryOptions",
    "InventoryDisabledError",
    "build_full_manifest",
    "collect_admin_inventory",
    "collect_core_inventory",
    "run_core_inventory_pipeline",
    "run_core_manifest_only",
    "run_full_inventory_pipeline",
]
