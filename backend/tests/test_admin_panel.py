from tests.test_core import auth_header, credit


def test_user_detail_block_and_adjust(client):
    headers = auth_header(client)
    staff = client.post("/api/v1/admin/staff", json={"telegram_id": 700100200, "role": "ADMIN"}, headers=headers)
    uid = staff.json()["data"]["id"]
    detail = client.get(f"/api/v1/admin/users/{uid}", headers=headers)
    assert detail.status_code == 200, detail.text
    data = detail.json()["data"]
    assert data["user"]["telegram_id"] == 700100200
    assert "orders" in data and "transactions" in data and "payments" in data
    blocked = client.patch(f"/api/v1/admin/users/{uid}", json={"is_blocked": True}, headers=headers)
    assert blocked.status_code == 200
    assert blocked.json()["data"]["is_blocked"] is True
    adj = client.patch(
        f"/api/v1/admin/users/{uid}",
        json={"adjust_amount": "150.00", "adjust_reason": "тест"},
        headers=headers,
    )
    assert adj.status_code == 200, adj.text
    assert adj.json()["data"]["balance"] == "150.00"
    txs = client.get("/api/v1/admin/transactions", headers=headers)
    assert txs.status_code == 200
    types = [t["type"] for t in txs.json()["data"]["items"]]
    assert "ADMIN_ADJUSTMENT" in types


def test_cannot_block_owner(client):
    headers = auth_header(client)
    owner = client.post("/api/v1/admin/staff", json={"telegram_id": 8565986003}, headers=headers).json()["data"]
    res = client.patch(f"/api/v1/admin/users/{owner['id']}", json={"is_blocked": True}, headers=headers)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "OWNER_PROTECTED"


def test_overview_has_payments(client):
    headers = auth_header(client)
    client.post("/api/v1/trust-pay/payments", json={"amount": "100"}, headers=headers)
    ov = client.get("/api/v1/admin/overview?period=7d", headers=headers)
    assert ov.status_code == 200
    data = ov.json()["data"]
    assert "pending_payments" in data
    assert int(data["pending_payments"]) >= 1


def test_order_status_guard(client):
    headers = auth_header(client)
    catalog = client.get("/api/v1/catalog", headers=headers).json()["data"]["items"]
    stars = next(p for p in catalog if p["kind"] == "stars")
    credit(client, headers, "500")
    order = client.post(
        "/api/v1/orders",
        json={"product_id": stars["id"], "quantity": 50, "recipient": "durov", "idempotency_key": "adm-order-status-01"},
        headers=headers,
    ).json()["data"]
    bad = client.patch(f"/api/v1/admin/orders/{order['public_id']}", json={"status": "PENDING"}, headers=headers)
    assert bad.status_code == 400
    ok = client.patch(f"/api/v1/admin/orders/{order['public_id']}", json={"status": "COMPLETED"}, headers=headers)
    assert ok.status_code == 200, ok.text
    assert ok.json()["data"]["status"] == "COMPLETED"
    detail = client.get(f"/api/v1/admin/orders/{order['public_id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["data"]["user"]["id"]
