"""Tests for the bearer-token gate on /api/v1 routes (services/auth.py)."""
import pytest
from httpx import AsyncClient

from app.config import settings

pytestmark = pytest.mark.asyncio

_TOKEN = "test-api-token"


@pytest.fixture
def api_token(monkeypatch: pytest.MonkeyPatch) -> str:
    """Configure an API token for the duration of a test."""
    monkeypatch.setattr(settings, "api_token", _TOKEN)
    return _TOKEN


async def test_missing_token_is_rejected(client: AsyncClient, api_token: str) -> None:
    """Requests without an Authorization header get 401 when a token is configured."""
    resp = await client.get("/api/v1/transactions")
    assert resp.status_code == 401


async def test_wrong_token_is_rejected(client: AsyncClient, api_token: str) -> None:
    """Requests with the wrong bearer token get 401."""
    resp = await client.get(
        "/api/v1/transactions", headers={"Authorization": "Bearer nope"}
    )
    assert resp.status_code == 401


async def test_correct_token_is_accepted(client: AsyncClient, api_token: str) -> None:
    """Requests with the configured bearer token succeed."""
    resp = await client.get(
        "/api/v1/transactions", headers={"Authorization": f"Bearer {api_token}"}
    )
    assert resp.status_code == 200


async def test_every_api_router_is_protected(client: AsyncClient, api_token: str) -> None:
    """Each /api/v1 router rejects unauthenticated requests."""
    for method, path in [
        ("GET", "/api/v1/summary"),
        ("GET", "/api/v1/insights"),
        ("GET", "/api/v1/categories"),
        ("GET", "/api/v1/charts/donut"),
        ("POST", "/api/v1/ai/parse"),
        ("DELETE", "/api/v1/transactions/00000000-0000-0000-0000-000000000000"),
    ]:
        resp = await client.request(method, path)
        assert resp.status_code == 401, f"{method} {path} returned {resp.status_code}"


async def test_unconfigured_token_fails_closed_in_production(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no API_TOKEN set, production refuses every API request."""
    monkeypatch.setattr(settings, "api_token", "")
    monkeypatch.setattr(settings, "environment", "production")
    resp = await client.get("/api/v1/transactions")
    assert resp.status_code == 503


async def test_health_and_dashboard_stay_public(client: AsyncClient, api_token: str) -> None:
    """The health check and the dashboard page don't require a token."""
    assert (await client.get("/health")).status_code == 200
    assert (await client.get("/")).status_code == 200
