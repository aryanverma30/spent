"""Integration tests for POST/GET/PATCH/DELETE /api/v1/transactions."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

_PAYLOAD = {
    "amount": 12.50,
    "merchant": "Chipotle",
    "category": "Food & Drink",
    "raw_input": "$12.50 Chipotle",
    "ai_confidence": 0.95,
}


async def test_create_transaction_returns_201(client: AsyncClient) -> None:
    """POST /transactions creates a record and returns HTTP 201."""
    resp = await client.post("/api/v1/transactions", json=_PAYLOAD)
    assert resp.status_code == 201
    body = resp.json()
    assert body["merchant"] == "Chipotle"
    assert float(body["amount"]) == 12.50
    assert body["category"] == "Food & Drink"
    assert "id" in body


async def test_list_transactions_returns_list(client: AsyncClient) -> None:
    """GET /transactions returns a JSON array (possibly empty)."""
    resp = await client.get("/api/v1/transactions")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_list_transactions_includes_created_record(client: AsyncClient) -> None:
    """A created transaction appears in the GET list."""
    await client.post("/api/v1/transactions", json=_PAYLOAD)
    resp = await client.get("/api/v1/transactions")
    assert resp.status_code == 200
    merchants = [t["merchant"] for t in resp.json()]
    assert "Chipotle" in merchants


async def test_patch_updates_category(client: AsyncClient) -> None:
    """PATCH /transactions/{id} updates the category field."""
    create_resp = await client.post("/api/v1/transactions", json=_PAYLOAD)
    transaction_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/transactions/{transaction_id}",
        json={"category": "Shopping"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["category"] == "Shopping"


async def test_delete_returns_204(client: AsyncClient) -> None:
    """DELETE /transactions/{id} returns HTTP 204."""
    create_resp = await client.post("/api/v1/transactions", json=_PAYLOAD)
    transaction_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/api/v1/transactions/{transaction_id}")
    assert delete_resp.status_code == 204


async def test_get_deleted_transaction_returns_404(client: AsyncClient) -> None:
    """A subsequent GET for a deleted transaction returns HTTP 404."""
    create_resp = await client.post("/api/v1/transactions", json=_PAYLOAD)
    transaction_id = create_resp.json()["id"]

    await client.delete(f"/api/v1/transactions/{transaction_id}")

    get_resp = await client.get("/api/v1/transactions", params={"limit": 100})
    ids = [t["id"] for t in get_resp.json()]
    assert transaction_id not in ids
