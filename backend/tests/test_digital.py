from datetime import datetime, timedelta, timezone

from tests.test_core import auth_header, credit


def _gplay(client, headers):
    items = client.get("/api/v1/digital/catalog", headers=headers).json()["data"]["items"]
    return next(p for p in items if p["category"] == "google_play")


def _steam(client, headers):
    items = client.get("/api/v1/digital/catalog", headers=headers).json()["data"]["items"]
    return next(p for p in items if p["category"] == "steam")


def test_digital_catalog_and_out_of_stock(client):
    headers = auth_header(client)
    cat = client.get("/api/v1/digital/catalog", headers=headers)
    assert cat.status_code == 200
    card = _gplay(client, headers)
    assert card["in_stock"] is False
    buy = client.post(
        "/api/v1/digital/orders",
        json={"product_id": card["id"], "idempotency_key": "no-stock-key-1"},
        headers=headers,
    )
    assert buy.status_code == 400
    assert buy.json()["error"]["code"] == "OUT_OF_STOCK"


def test_digital_code_sold_once(client):
    headers = auth_header(client)
    card = _gplay(client, headers)
    add = client.post(
        f"/api/v1/admin/digital/{card['id']}/codes",
        json={"codes": "GPLAY-TEST-AAAA\nGPLAY-TEST-AAAA"},
        headers=headers,
    )
    assert add.status_code == 200, add.text
    assert add.json()["data"]["added"] == 1
    credit(client, headers, "2000")
    first = client.post(
        "/api/v1/digital/orders",
        json={"product_id": card["id"], "idempotency_key": "buy-gplay-once"},
        headers=headers,
    )
    assert first.status_code == 200, first.text
    data = first.json()["data"]
    assert data["status"] == "completed"
    assert data["code"] == "GPLAY-TEST-AAAA"
    again = client.post(
        "/api/v1/digital/orders",
        json={"product_id": card["id"], "idempotency_key": "buy-gplay-once"},
        headers=headers,
    )
    assert again.json()["data"]["public_id"] == data["public_id"]
    second = client.post(
        "/api/v1/digital/orders",
        json={"product_id": card["id"], "idempotency_key": "buy-gplay-two"},
        headers=headers,
    )
    assert second.status_code == 400
    got = client.get(f"/api/v1/digital/orders/{data['public_id']}", headers=headers).json()["data"]
    assert got["code"] == "GPLAY-TEST-AAAA"


def test_steam_custom_amount_by_login(client):
    headers = auth_header(client)
    steam = _steam(client, headers)
    assert steam["amount_mode"] == "custom"
    assert steam["in_stock"] is True
    credit(client, headers, "2000")
    miss = client.post(
        "/api/v1/digital/orders",
        json={"product_id": steam["id"], "extra": {"amount": "500"}, "idempotency_key": "steam-miss-login"},
        headers=headers,
    )
    assert miss.json()["error"]["code"] == "MISSING_FIELD"
    no_amt = client.post(
        "/api/v1/digital/orders",
        json={"product_id": steam["id"], "extra": {"steam_login": "playerone"}, "idempotency_key": "steam-miss-amt"},
        headers=headers,
    )
    assert no_amt.json()["error"]["code"] == "INVALID_AMOUNT"
    tiny = client.post(
        "/api/v1/digital/orders",
        json={"product_id": steam["id"], "extra": {"steam_login": "playerone", "amount": "50"}, "idempotency_key": "steam-tiny"},
        headers=headers,
    )
    assert tiny.json()["error"]["code"] == "INVALID_AMOUNT"
    before = float(client.get("/api/v1/me", headers=headers).json()["data"]["balance"])
    ok = client.post(
        "/api/v1/digital/orders",
        json={"product_id": steam["id"], "extra": {"steam_login": "playerone", "amount": "500"}, "idempotency_key": "steam-ok-1"},
        headers=headers,
    )
    assert ok.status_code == 200, ok.text
    data = ok.json()["data"]
    assert data["status"] == "processing"
    assert data["extra"]["steam_login"] == "playerone"
    assert data["price"] == "512.50"
    after = float(client.get("/api/v1/me", headers=headers).json()["data"]["balance"])
    assert round(before - after, 2) == 512.50


def test_roblox_requires_username(client):
    headers = auth_header(client)
    items = client.get("/api/v1/digital/catalog?group=games", headers=headers).json()["data"]["items"]
    roblox = next(p for p in items if p["category"] == "roblox")
    client.post(f"/api/v1/admin/digital/{roblox['id']}/codes", json={"codes": "ROBLOX-KEY-1"}, headers=headers)
    credit(client, headers, "2000")
    miss = client.post(
        "/api/v1/digital/orders",
        json={"product_id": roblox["id"], "idempotency_key": "rbx-miss"},
        headers=headers,
    )
    assert miss.json()["error"]["code"] == "MISSING_FIELD"
    ok = client.post(
        "/api/v1/digital/orders",
        json={"product_id": roblox["id"], "extra": {"username": "builderman"}, "idempotency_key": "rbx-ok-1"},
        headers=headers,
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["data"]["extra"]["username"] == "builderman"


def test_giveaway_join_once_and_balance_prize(client):
    headers = auth_header(client)
    created = client.post(
        "/api/v1/admin/giveaways",
        json={
            "title": "500 на баланс",
            "reward_type": "balance",
            "reward_amount": "500",
            "winner_count": 1,
            "finish_type": "count",
            "max_participants": 1,
        },
        headers=headers,
    )
    assert created.status_code == 200, created.text
    gid = created.json()["data"]["id"]
    before = float(client.get("/api/v1/me", headers=headers).json()["data"]["balance"])
    join = client.post(f"/api/v1/giveaways/{gid}/join", headers=headers)
    assert join.status_code == 200, join.text
    dup = client.post(f"/api/v1/giveaways/{gid}/join", headers=headers)
    assert dup.status_code == 400
    after = float(client.get("/api/v1/me", headers=headers).json()["data"]["balance"])
    assert round(after - before, 2) == 500.00
    detail = client.get(f"/api/v1/giveaways/{gid}", headers=headers).json()["data"]
    assert detail["status"] == "finished"
    assert detail["won"] is True


def test_giveaway_rejects_past_date(client):
    headers = auth_header(client)
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    res = client.post(
        "/api/v1/admin/giveaways",
        json={"title": "Старый", "reward_type": "balance", "reward_amount": "10", "finish_type": "time", "finish_at": past},
        headers=headers,
    )
    assert res.status_code == 400


def test_giveaway_product_prize_does_not_charge(client):
    headers = auth_header(client)
    card = _gplay(client, headers)
    client.post(f"/api/v1/admin/digital/{card['id']}/codes", json={"codes": "GIVE-GPLAY-1"}, headers=headers)
    created = client.post(
        "/api/v1/admin/giveaways",
        json={
            "title": "Google Play ключ",
            "reward_type": "product",
            "reward_product_id": card["id"],
            "winner_count": 1,
            "finish_type": "count",
            "max_participants": 1,
        },
        headers=headers,
    )
    assert created.status_code == 200, created.text
    gid = created.json()["data"]["id"]
    before = float(client.get("/api/v1/me", headers=headers).json()["data"]["balance"])
    join = client.post(f"/api/v1/giveaways/{gid}/join", headers=headers)
    assert join.status_code == 200, join.text
    after = float(client.get("/api/v1/me", headers=headers).json()["data"]["balance"])
    assert round(after - before, 2) == 0
    detail = client.get(f"/api/v1/giveaways/{gid}", headers=headers).json()["data"]
    assert detail["won"] is True
    assert detail["prize_code"] == "GIVE-GPLAY-1"
    purchases = client.get("/api/v1/digital/orders", headers=headers).json()["data"]["items"]
    assert any(o["price"] == "0.00" for o in purchases)
