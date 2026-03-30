from unittest.mock import MagicMock, patch

from fabric_provisioner.fabric_client import FabricClient


def test_request_get_retries_429_then_succeeds() -> None:
    r429 = MagicMock()
    r429.status_code = 429
    r429.headers = {"Retry-After": "0"}
    r_ok = MagicMock()
    r_ok.status_code = 200
    r_ok.json.return_value = {"value": [], "continuationToken": None}

    client = FabricClient(
        base_url="https://api.fabric.microsoft.com/v1",
        access_token="x",
    )
    mock_get = MagicMock(side_effect=[r429, r_ok])
    with (
        patch.object(client._client, "get", mock_get),
        patch("fabric_provisioner.fabric_client.time.sleep"),
    ):
        out = client.list_workspaces_page()

    assert out == {"value": [], "continuationToken": None}
    assert mock_get.call_count == 2
