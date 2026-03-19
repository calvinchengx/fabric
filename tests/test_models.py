import pytest
from pydantic import ValidationError

from fabric_provisioner.models import GroupRoleSpec, ServicePrincipalRoleSpec


def test_group_role_spec_accepts_member() -> None:
    g = GroupRoleSpec(object_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", role="Member")
    assert g.role == "Member"


def test_group_role_spec_rejects_invalid_role() -> None:
    with pytest.raises(ValidationError):
        GroupRoleSpec(object_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", role="Owner")


def test_spn_role_spec_accepts_viewer() -> None:
    s = ServicePrincipalRoleSpec(
        object_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", role="Viewer"
    )
    assert s.role == "Viewer"


def test_spn_role_spec_rejects_invalid_role() -> None:
    with pytest.raises(ValidationError):
        ServicePrincipalRoleSpec(
            object_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", role="Owner"
        )
