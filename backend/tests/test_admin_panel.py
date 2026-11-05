"""Admin panel: stats, user management, payment tracking, CLI."""

from __future__ import annotations

from app.core.config import settings
from app.db.models import User
from tests.conftest import register
from tests.test_shop import _product

SHIPPING = {"shipping_name": "Sara", "shipping_phone": "03001234567",
            "shipping_address": "Block A, Road 5", "shipping_city": "Lahore"}


def _admin(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_emails", "boss@test.com")
    return register(client, "boss@test.com")


def test_admin_endpoints_require_admin(api, monkeypatch):
    client, _ = api
    user = register(client, "plain@test.com")
    for path in ["/admin/stats", "/admin/users"]:
        assert client.get(path).status_code == 401
        assert client.get(path, headers=user).status_code == 403


def test_stats_and_payment_flow(api, monkeypatch):
    client, _ = api
    admin = _admin(client, monkeypatch)
    pid = client.post("/admin/products", json=_product(stock=3), headers=admin).json()["id"]
    buyer = register(client, "buyer2@test.com")
    client.post("/cart/items", json={"product_id": pid, "quantity": 2}, headers=buyer)
    order = client.post("/orders", json=SHIPPING, headers=buyer).json()
    assert order["payment_status"] == "unpaid"

    stats = client.get("/admin/stats", headers=admin).json()
    assert stats["users"]["total"] == 2 and stats["users"]["admins"] == 1
    assert stats["orders"]["by_status"]["pending"] == 1
    assert stats["payments"]["outstanding"] == 2400.0
    assert stats["products"]["low_stock"] == 1

    # Cannot refund before payment; mark paid after delivery
    assert client.patch(f"/admin/orders/{order['id']}", json={"payment_status": "refunded"},
                        headers=admin).status_code == 409
    paid = client.patch(f"/admin/orders/{order['id']}", json={"status": "confirmed", "payment_status": "paid"},
                        headers=admin).json()
    assert paid["status"] == "confirmed" and paid["payment_status"] == "paid"
    assert client.get("/admin/stats", headers=admin).json()["payments"]["collected"] == 2400.0
    assert client.get("/orders", headers=buyer).json()[0]["payment_status"] == "paid"


def test_user_management(api, monkeypatch):
    client, SessionLocal = api
    admin = _admin(client, monkeypatch)
    register(client, "member@test.com")

    users = client.get("/admin/users", headers=admin).json()
    member = next(u for u in users if u["email"] == "member@test.com")
    me = next(u for u in users if u["email"] == "boss@test.com")

    promoted = client.patch(f"/admin/users/{member['id']}", json={"role": "admin"}, headers=admin).json()
    assert promoted["role"] == "admin"

    assert client.patch(f"/admin/users/{me['id']}", json={"role": "user"}, headers=admin).status_code == 400
    assert client.patch(f"/admin/users/{me['id']}", json={"is_active": False}, headers=admin).status_code == 400

    found = client.get("/admin/users", params={"q": "member"}, headers=admin).json()
    assert [u["email"] for u in found] == ["member@test.com"]


def test_cli_make_admin(api, monkeypatch, capsys):
    client, SessionLocal = api
    register(client, "cli@test.com")
    monkeypatch.setattr("app.cli.SessionLocal", SessionLocal)

    from app.cli import main

    assert main(["make-admin", "CLI@test.com"]) == 0
    with SessionLocal() as db:
        assert db.query(User).filter(User.email == "cli@test.com").one().role == "admin"
    assert main(["make-admin", "missing@test.com"]) == 1
    assert "cli@test.com" in (main(["list-admins"]) or capsys.readouterr().out)
