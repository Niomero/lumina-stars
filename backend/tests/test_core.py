import os
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("DEMO_LOGIN_ENABLED", "true")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-please-use-long-value")
os.environ.setdefault("SECRET_KEY", "test-secret-key-please-use-long-value")

from app.core.config import get_settings

get_settings.cache_clear()

from app.core.money import apply_markup, money
from app.core.rbac import Role, has_permission
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.services.bootstrap import seed


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Testing = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)
    db = Testing()
    seed(db)
    db.close()

    def _get_db():
        session = Testing()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def auth_header(client: TestClient) -> dict:
    res = client.post("/api/v1/auth/demo", json={"name": "Tester"})
    assert res.status_code == 200, res.text
    token = res.json()["data"]["token"]
    return {"Authorization": f"Bearer {token}"}


def test_money_decimal_not_float():
    assert money("1.239") == Decimal("1.24")
    assert apply_markup(Decimal("100.00"), 10, 0) == Decimal("110.00")


def test_rbac():
    assert has_permission(Role.USER, "catalog.read")
    assert not has_permission(Role.USER, "balance.adjust")
    assert has_permission(Role.SUPERADMIN, "balance.adjust")


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["data"]["ok"] is True


def test_demo_auth_and_balance(client):
    headers = auth_header(client)
    me = client.get("/api/v1/me", headers=headers).json()["data"]
    assert me["role"] == "SUPERADMIN"
    assert float(me["balance"]) >= 0
    cat = client.get("/api/v1/catalog", headers=headers).json()["data"]["items"]
    assert any(p["kind"] == "stars" for p in cat)


def test_checkout_and_idempotency(client):
    headers = auth_header(client)
    client.post("/api/v1/balance/deposit", json={"amount": "5000"}, headers=headers)
    catalog = client.get("/api/v1/catalog", headers=headers).json()["data"]["items"]
    stars = next(p for p in catalog if p["kind"] == "stars")
    payload = {
        "product_id": stars["id"],
        "quantity": 100,
        "recipient": "durov",
        "idempotency_key": "abc12345-test-key",
    }
    first = client.post("/api/v1/orders", json=payload, headers=headers)
    assert first.status_code == 200, first.text
    order = first.json()["data"]
    assert order["status"] == "APPROVED"
    assert "одобрен" in (order.get("headline") or "").lower() or order["status"] == "APPROVED"
    second = client.post("/api/v1/orders", json=payload, headers=headers)
    assert second.json()["data"]["public_id"] == order["public_id"]


def test_insufficient_balance(client):
    headers = auth_header(client)
    me = client.get("/api/v1/me", headers=headers).json()["data"]
    catalog = client.get("/api/v1/catalog", headers=headers).json()["data"]["items"]
    stars = next(p for p in catalog if p["kind"] == "stars")
    payload = {
        "product_id": stars["id"],
        "quantity": 10000,
        "recipient": "durov",
        "idempotency_key": "low-balance-key-0001",
    }
    res = client.post("/api/v1/orders", json=payload, headers=headers)
    if float(me["balance"]) < 18000:
        assert res.status_code == 402
        assert res.json()["error"]["code"] == "INSUFFICIENT_BALANCE"


def test_referral_code_present(client):
    headers = auth_header(client)
    ref = client.get("/api/v1/referrals", headers=headers).json()["data"]
    assert ref["code"]
    assert ref["enabled"] is True


def test_nft_rent_demo_checkout(client):
    headers = auth_header(client)
    client.post("/api/v1/balance/deposit", json={"amount": "5000"}, headers=headers)
    catalog = client.get("/api/v1/catalog", headers=headers).json()["data"]["items"]
    nft = next(p for p in catalog if p["kind"] == "nft_rent")
    listing = client.get("/api/v1/rent/nft/list", headers=headers).json()["data"]["items"]
    assert listing
    asset = listing[0]
    res = client.post(
        "/api/v1/orders",
        json={
            "product_id": nft["id"],
            "quantity": 7,
            "nft_address": asset["address"],
            "idempotency_key": "nft-rent-demo-key-01",
        },
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "APPROVED"
    assert res.json()["data"]["recipient"] == asset["address"]
    connect = client.post(
        "/api/v1/rent/connect",
        json={"order_id": res.json()["data"]["id"], "tonconnect_url": "tc://demo"},
        headers=headers,
    )
    assert connect.status_code == 200, connect.text
    assert connect.json()["data"]["demo"] is True


def test_nft_buy_and_transfer_demo(client):
    headers = auth_header(client)
    client.post("/api/v1/balance/deposit", json={"amount": "20000"}, headers=headers)
    catalog = client.get("/api/v1/catalog", headers=headers).json()["data"]["items"]
    buy = next(p for p in catalog if p["kind"] == "nft_buy")
    listing = client.get("/api/v1/nft/buy/list", headers=headers).json()["data"]["items"]
    asset = listing[0]
    res = client.post(
        "/api/v1/orders",
        json={
            "product_id": buy["id"],
            "quantity": 1,
            "nft_address": asset["address"],
            "idempotency_key": "nft-buy-demo-key-01",
        },
        headers=headers,
    )
    assert res.status_code == 200, res.text
    order = res.json()["data"]
    xfer = client.post(
        "/api/v1/nft/transfer",
        json={"order_id": order["id"], "destination": "telegram", "username": "durov"},
        headers=headers,
    )
    assert xfer.status_code == 200, xfer.text
    assert xfer.json()["data"]["demo"] is True


def test_username_rent_filters(client):
    headers = auth_header(client)
    data = client.get("/api/v1/rent/username/list?length_filter=4", headers=headers).json()["data"]
    assert data["items"]
    assert all(int(i["length"]) == 4 for i in data["items"])
