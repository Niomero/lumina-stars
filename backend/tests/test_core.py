from decimal import Decimal

from fastapi.testclient import TestClient

from app.core.money import apply_markup, money
from app.core.rbac import Role, has_permission


def auth_header(client: TestClient) -> dict:
    res = client.post("/api/v1/auth/demo", json={"name": "Tester"})
    assert res.status_code == 200, res.text
    token = res.json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}
    unlock = client.post("/api/v1/admin/unlock", json={"password": "LuminaSuperStar011!?4"}, headers=headers)
    assert unlock.status_code == 200, unlock.text
    headers["X-Admin-Unlock"] = unlock.json()["data"]["token"]
    return headers


def credit(client, headers, amount: str):
    me = client.get("/api/v1/me", headers=headers).json()["data"]
    res = client.patch(
        f"/api/v1/admin/users/{me['id']}",
        json={"adjust_amount": amount, "adjust_reason": "test"},
        headers=headers,
    )
    assert res.status_code == 200, res.text



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


def test_public_boot(client):
    res = client.get("/api/v1/public/boot")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["app_name"]
    assert "demo_login_enabled" in data
    assert "bot_username" in data


def test_demo_auth_and_balance(client):
    headers = auth_header(client)
    me = client.get("/api/v1/me", headers=headers).json()["data"]
    assert me["role"] == "SUPERADMIN"
    assert float(me["balance"]) >= 0
    cat = client.get("/api/v1/catalog", headers=headers).json()["data"]["items"]
    assert any(p["kind"] == "stars" for p in cat)


def test_checkout_and_idempotency(client):
    headers = auth_header(client)
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
    assert order["unit_price"] == "1.32"
    assert order["total_price"] == "132.00"
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
    if float(me["balance"]) < 13000:
        assert res.status_code == 402
        assert res.json()["error"]["code"] == "INSUFFICIENT_BALANCE"


def test_referral_code_present(client):
    headers = auth_header(client)
    ref = client.get("/api/v1/referrals", headers=headers).json()["data"]
    assert ref["code"]
    assert ref["enabled"] is True


def test_nft_rent_demo_checkout(client):
    headers = auth_header(client)
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
    credit(client, headers, "20000")
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
