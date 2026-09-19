from decimal import Decimal

from tests.test_core import auth_header, credit


def test_admin_creates_and_lists_promos(client):
    headers = auth_header(client)
    created = client.post(
        "/api/v1/admin/promos",
        json={"code": "gift50", "kind": "balance", "amount_type": "fixed", "amount": "50.00", "note": "тест"},
        headers=headers,
    )
    assert created.status_code == 200, created.text
    data = created.json()["data"]
    assert data["code"] == "GIFT50"
    assert data["kind"] == "balance"
    listed = client.get("/api/v1/admin/promos", headers=headers)
    assert listed.status_code == 200
    codes = [p["code"] for p in listed.json()["data"]["items"]]
    assert "GIFT50" in codes


def test_redeem_balance_promo(client):
    headers = auth_header(client)
    me = client.get("/api/v1/me", headers=headers).json()["data"]
    before = Decimal(me["balance"])
    client.post(
        "/api/v1/admin/promos",
        json={"code": "PLUS100", "kind": "balance", "amount": "100.00"},
        headers=headers,
    )
    res = client.post("/api/v1/promos/redeem", json={"code": "plus100"}, headers=headers)
    assert res.status_code == 200, res.text
    assert Decimal(res.json()["data"]["credited"]) == Decimal("100.00")
    me2 = client.get("/api/v1/me", headers=headers).json()["data"]
    assert Decimal(me2["balance"]) == before + Decimal("100.00")
    again = client.post("/api/v1/promos/redeem", json={"code": "PLUS100"}, headers=headers)
    assert again.status_code == 400
    assert again.json()["error"]["code"] == "PROMO_USED"


def test_discount_promo_on_checkout(client):
    headers = auth_header(client)
    credit(client, headers, "500")
    catalog = client.get("/api/v1/catalog", headers=headers).json()["data"]["items"]
    stars = next(p for p in catalog if p["kind"] == "stars")
    client.post(
        "/api/v1/admin/promos",
        json={"code": "SALE10", "kind": "discount", "amount_type": "percent", "amount": "10"},
        headers=headers,
    )
    preview = client.get(
        f"/api/v1/promos/preview?code=SALE10&product_id={stars['id']}&quantity=100",
        headers=headers,
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["data"]["valid"] is True
    order = client.post(
        "/api/v1/orders",
        json={
            "product_id": stars["id"],
            "quantity": 100,
            "recipient": "durov",
            "idempotency_key": "promo-sale10-order",
            "promo_code": "SALE10",
        },
        headers=headers,
    )
    assert order.status_code == 200, order.text
    data = order.json()["data"]
    assert data["promo"] == "SALE10"
    assert Decimal(data["total_price"]) == Decimal("118.80")
    assert data["discount"] == "13.20"


def test_product_promo_rejects_other_item(client):
    headers = auth_header(client)
    catalog = client.get("/api/v1/catalog", headers=headers).json()["data"]["items"]
    stars = next(p for p in catalog if p["kind"] == "stars")
    premium = next(p for p in catalog if p["kind"] == "premium")
    client.post(
        "/api/v1/admin/promos",
        json={
            "code": "STARSONLY",
            "kind": "product",
            "amount_type": "percent",
            "amount": "100",
            "product_id": stars["id"],
        },
        headers=headers,
    )
    bad = client.get(
        f"/api/v1/promos/preview?code=STARSONLY&product_id={premium['id']}&quantity={premium['min_quantity']}",
        headers=headers,
    )
    assert bad.status_code == 400
    assert bad.json()["error"]["code"] == "PROMO_WRONG_PRODUCT"
    ok = client.get(
        f"/api/v1/promos/preview?code=STARSONLY&product_id={stars['id']}&quantity=50",
        headers=headers,
    )
    assert ok.status_code == 200, ok.text
    assert Decimal(ok.json()["data"]["new_total"]) == Decimal("0.00")
