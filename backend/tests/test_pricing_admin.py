from decimal import Decimal

from tests.test_core import auth_header, credit


def test_admin_requires_password(client):
    res = client.post("/api/v1/auth/demo", json={"name": "Tester"})
    token = res.json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}
    locked = client.get("/api/v1/admin/overview", headers=headers)
    assert locked.status_code == 403
    assert locked.json()["error"]["code"] == "ADMIN_LOCKED"
    bad = client.post("/api/v1/admin/unlock", json={"password": "wrong"}, headers=headers)
    assert bad.status_code == 403
    ok = client.post("/api/v1/admin/unlock", json={"password": "LuminaSuperStar011!?4"}, headers=headers)
    assert ok.status_code == 200, ok.text
    headers["X-Admin-Unlock"] = ok.json()["data"]["token"]
    ov = client.get("/api/v1/admin/overview", headers=headers)
    assert ov.status_code == 200


def test_api_markup_changes_stars_price(client):
    headers = auth_header(client)
    put = client.put("/api/v1/admin/pricing", json={"global_percent": "10"}, headers=headers)
    assert put.status_code == 200, put.text
    catalog = client.get("/api/v1/catalog", headers=headers).json()["data"]["items"]
    stars = next(p for p in catalog if p["kind"] == "stars")
    assert Decimal(stars["unit_price"]) == Decimal("1.45")
    credit(client, headers, "500")
    order = client.post(
        "/api/v1/orders",
        json={"product_id": stars["id"], "quantity": 100, "recipient": "durov", "idempotency_key": "markup-10-order"},
        headers=headers,
    )
    assert order.status_code == 200, order.text
    assert Decimal(order.json()["data"]["total_price"]) == Decimal("145.00")


def test_sale_discounts_catalog(client):
    headers = auth_header(client)
    sale = client.post(
        "/api/v1/admin/sales",
        json={"name": "Весенняя", "percent": "20", "categories": "stars", "enabled": True},
        headers=headers,
    )
    assert sale.status_code == 200, sale.text
    catalog = client.get("/api/v1/catalog", headers=headers).json()["data"]["items"]
    stars = next(p for p in catalog if p["kind"] == "stars")
    assert Decimal(stars["sale_percent"]) == Decimal("20.00")
    assert Decimal(stars["unit_price"]) == Decimal("1.06")
    assert stars["compare_at"] is not None
