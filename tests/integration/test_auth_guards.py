"""Integration tests verifying the regular-only authentication guard."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_regular_user_header_allows_market_access(client) -> None:  # noqa: ANN001
    """Ensure the happy path still works when the regular session header is present."""

    response = client.get(
        "/api/v1/market/ohlcv",
        params={"symbol": "BTCUSD", "timeframe": "1h", "limit": 10},
    )
    assert response.status_code == 200


def test_missing_user_type_header_is_rejected(test_app) -> None:  # noqa: ANN001
    """Requests without ``X-User-Type`` should be forbidden despite a valid token."""

    with TestClient(test_app) as anonymous_client:
        anonymous_client.headers.update({"Authorization": "Bearer testingtoken"})
        response = anonymous_client.get(
            "/api/v1/market/ohlcv",
            params={"symbol": "BTCUSD", "timeframe": "1h", "limit": 10},
        )
    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "forbidden:chat"
    assert payload["error"]["message"] == "Regular session required"


def test_guest_user_is_blocked_from_data_routes(test_app) -> None:  # noqa: ANN001
    """Guest sessions should receive a structured 403 payload."""

    with TestClient(test_app) as guest_client:
        guest_client.headers.update(
            {
                "Authorization": "Bearer testingtoken",
                "X-User-Type": "guest",
            }
        )
        response = guest_client.get(
            "/api/v1/market/ohlcv",
            params={"symbol": "BTCUSD", "timeframe": "1h", "limit": 10},
        )
    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "forbidden:chat"
    assert payload["error"]["message"] == "Regular session required"
