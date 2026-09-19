from decimal import Decimal

from app.core.errors import AppError
from app.core.money import money, percent_of
from app.services.trust_pay import copy_card, topup_reply, yoomoney_url
from tests.test_core import auth_header


def test_fee_examples():
    assert percent_of(Decimal("30"), 3) == Decimal("0.90")
    assert percent_of(Decimal("100"), 3) == Decimal("3.00")
    assert percent_of(Decimal("500"), 3) == Decimal("15.00")
    assert percent_of(Decimal("1000"), 3) == Decimal("30.00")
    assert money(Decimal("500") + Decimal("15")) == Decimal("515.00")


def test_card_and_yoomoney_helpers():
    assert copy_card("5599002144955509") == "5599 0021 4495 5509"
    url = yoomoney_url("515")
    assert url == "https://yoomoney.ru/to/4100119621450464/515"
    assert not url.endswith("/0")
    try:
        yoomoney_url("0")
        assert False, "expected amount required"
    except AppError as exc:
        assert exc.code == "AMOUNT_REQUIRED"


def test_min_amount_rejected(client):
    headers = auth_header(client)
    res = client.post("/api/v1/trust-pay/payments", json={"amount": "10"}, headers=headers)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "MIN_AMOUNT"
    assert "30" in res.json()["error"]["message"]


def test_create_and_user_paid_does_not_credit(client):
    headers = auth_header(client)
    before = float(client.get("/api/v1/me", headers=headers).json()["data"]["balance"])
    res = client.post("/api/v1/trust-pay/payments", json={"amount": "500"}, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["public_id"].startswith("TP-")
    assert data["amount"] == "500.00"
    assert data["fee"] == "15.00"
    assert data["total"] == "515.00"
    assert data["status"] == "pending"
    assert "amount=" not in (data.get("pay_url") or "")
    assert data["card_masked"].startswith("5599")
    assert data["card_masked"].endswith("5509")
    assert data.get("card_copy")
    assert data["card_copy"].replace(" ", "") == "5599002144955509"
    assert data["card_copy"] == "5599 0021 4495 5509"
    assert data["yoomoney_url"] == "https://yoomoney.ru/to/4100119621450464/515"

    paid = client.post(f"/api/v1/trust-pay/payments/{data['public_id']}/paid", headers=headers)
    assert paid.status_code == 200, paid.text
    assert paid.json()["data"]["status"] == "processing"
    after = float(client.get("/api/v1/me", headers=headers).json()["data"]["balance"])
    assert after == before


def test_admin_confirm_credits_amount_once(client):
    headers = auth_header(client)
    me = client.get("/api/v1/me", headers=headers).json()["data"]
    before = float(me["balance"])
    created = client.post("/api/v1/trust-pay/payments", json={"amount": "100"}, headers=headers).json()["data"]
    client.post(f"/api/v1/trust-pay/payments/{created['public_id']}/paid", headers=headers)
    first = client.post(f"/api/v1/admin/trust-pay/{created['id']}/confirm", headers=headers)
    assert first.status_code == 200, first.text
    assert first.json()["data"]["status"] == "paid"
    mid = float(client.get("/api/v1/me", headers=headers).json()["data"]["balance"])
    assert round(mid - before, 2) == 100.00
    second = client.post(f"/api/v1/admin/trust-pay/{created['id']}/confirm", headers=headers)
    assert second.status_code == 200
    end = float(client.get("/api/v1/me", headers=headers).json()["data"]["balance"])
    assert end == mid
    txs = client.get("/api/v1/transactions", headers=headers).json()["data"]["items"]
    deposits = [t for t in txs if t["type"] == "DEPOSIT" and created["public_id"] in (t.get("description") or "")]
    assert len(deposits) == 1
    assert deposits[0]["amount"] == "100.00"


def test_cannot_change_amount_via_query(client):
    headers = auth_header(client)
    created = client.post("/api/v1/trust-pay/payments", json={"amount": "30"}, headers=headers).json()["data"]
    got = client.get(f"/api/v1/trust-pay/payments/{created['public_id']}?amount=1", headers=headers).json()["data"]
    assert got["amount"] == "30.00"
    assert got["total"] == "30.90"
    assert got["yoomoney_url"] == "https://yoomoney.ru/to/4100119621450464/30.90"


def test_bot_topup_webhook_accepted(client):
    body = {
        "message": {
            "chat": {"id": 1},
            "from": {"id": 1, "username": "lumina", "first_name": "Lumina"},
            "text": "Пополнить баланс",
        }
    }
    res = client.post("/api/v1/telegram/webhook/lumina-hook", json=body)
    assert res.status_code == 200
    res2 = client.post(
        "/api/v1/telegram/webhook/lumina-hook",
        json={"message": {"chat": {"id": 1}, "from": {"id": 1, "first_name": "Lumina"}, "text": "10"}},
    )
    assert res2.status_code == 200


def test_topup_reply_opens_trust_pay_webapp(monkeypatch):
    from app.core.config import get_settings
    from app.services.trust_pay import pay_url, topup_reply

    monkeypatch.setenv("TELEGRAM_WEBAPP_URL", "https://lumina-stars.onrender.com/?v=c8bce14")
    get_settings.cache_clear()

    class P:
        public_id = "TP-TEST"
        amount = Decimal("500.00")
        fee = Decimal("15.00")
        total = Decimal("515.00")

    assert pay_url("TP-TEST") == "https://lumina-stars.onrender.com/pay/TP-TEST"
    text, markup = topup_reply(P())
    assert text.startswith("TRUST PAY")
    assert "Сумма пополнения: 500.00 ₽" in text
    assert "К оплате: 515.00 ₽" in text
    assert markup
    pay_btn = markup["inline_keyboard"][0][0]
    assert pay_btn["text"] == "Перейти к оплате"
    assert pay_btn["web_app"]["url"] == "https://lumina-stars.onrender.com/pay/TP-TEST"
    assert "?v=c8bce14/pay" not in pay_btn["web_app"]["url"]
    ym = markup["inline_keyboard"][1][0]
    assert ym["url"] == "https://yoomoney.ru/to/4100119621450464/515"
    get_settings.cache_clear()


def test_public_receipt(client):
    headers = auth_header(client)
    created = client.post("/api/v1/trust-pay/payments", json={"amount": "500"}, headers=headers).json()["data"]
    rec = client.get(f"/api/v1/trust-pay/receipt/{created['public_id']}")
    assert rec.status_code == 200, rec.text
    data = rec.json()["data"]
    assert data["amount"] == "500.00"
    assert data["total"] == "515.00"
    assert data["card_copy"] == "5599 0021 4495 5509"
