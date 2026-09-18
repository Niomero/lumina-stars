from app.core.config import get_settings
from app.core.security import create_access_token
from tests.test_core import auth_header


def test_add_admin_by_telegram_id(client):
    headers = auth_header(client)
    res = client.post("/api/v1/admin/staff", json={"telegram_id": 777000111, "role": "ADMIN"}, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["telegram_id"] == 777000111
    assert data["role"] == "ADMIN"
    assert data["is_owner"] is False
    staff = client.get("/api/v1/admin/staff", headers=headers).json()["data"]["items"]
    assert any(u["telegram_id"] == 777000111 and u["role"] == "ADMIN" for u in staff)


def test_owner_telegram_becomes_superadmin(client):
    headers = auth_header(client)
    owner_id = get_settings().owner_telegram_id
    res = client.post("/api/v1/admin/staff", json={"telegram_id": owner_id}, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["role"] == "SUPERADMIN"
    assert data["is_owner"] is True
    demote = client.patch(f"/api/v1/admin/users/{data['id']}", json={"role": "USER"}, headers=headers)
    assert demote.status_code == 400
    assert demote.json()["error"]["code"] == "OWNER_PROTECTED"
    drop = client.delete(f"/api/v1/admin/staff/{data['id']}", headers=headers)
    assert drop.status_code == 400
    assert drop.json()["error"]["code"] == "OWNER_PROTECTED"


def test_admin_cannot_add_staff(client):
    headers = auth_header(client)
    created = client.post("/api/v1/admin/staff", json={"telegram_id": 555111222, "role": "ADMIN"}, headers=headers)
    assert created.status_code == 200, created.text
    uid = created.json()["data"]["id"]
    token = create_access_token(uid, {"role": "ADMIN"})
    other = client.post(
        "/api/v1/admin/staff",
        json={"telegram_id": 555111223},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert other.status_code == 403


def test_remove_staff_and_username_lookup(client):
    headers = auth_header(client)
    created = client.post(
        "/api/v1/admin/staff",
        json={"telegram_id": 444111000, "username": "helper", "role": "MANAGER"},
        headers=headers,
    ).json()["data"]
    assert created["role"] == "MANAGER"
    found = client.post("/api/v1/admin/staff", json={"username": "@helper", "role": "ADMIN"}, headers=headers)
    assert found.status_code == 200
    assert found.json()["data"]["role"] == "ADMIN"
    drop = client.delete(f"/api/v1/admin/staff/{created['id']}", headers=headers)
    assert drop.status_code == 200
    assert drop.json()["data"]["role"] == "USER"


def test_cannot_assign_superadmin_role(client):
    headers = auth_header(client)
    created = client.post("/api/v1/admin/staff", json={"telegram_id": 333222111, "role": "ADMIN"}, headers=headers)
    uid = created.json()["data"]["id"]
    res = client.patch(f"/api/v1/admin/users/{uid}", json={"role": "SUPERADMIN"}, headers=headers)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVALID_ROLE"
    me = client.get("/api/v1/me", headers=headers).json()["data"]
    blocked = client.patch(f"/api/v1/admin/users/{me['id']}", json={"role": "ADMIN"}, headers=headers)
    assert blocked.status_code == 400
    assert blocked.json()["error"]["code"] == "OWNER_PROTECTED"
