"""Shop: admin product CRUD, ingredient search, cart, orders."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.db.models import Product, SkinAnalysis, User
from tests.conftest import register
from tests.helpers import make_skin_closeup, to_bytes


def _admin(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_emails", "admin@shop.com")
    return register(client, "admin@shop.com")


def _product(**overrides):
    data = {
        "name": "Clear Skin Gel Cleanser",
        "brand": "Brand A",
        "category": "Cleanser",
        "ingredients": "Aqua, Salicylic Acid, Niacinamide (Vitamin B3), Glycerin",
        "skin_types": ["Oily", "Combination"],
        "concerns": ["Acne", "Blackheads"],
        "price": 1200,
        "currency": "PKR",
        "price_source": "Brand A official store",
        "price_checked_at": datetime.now(timezone.utc).isoformat(),
        "stock": 5,
    }
    data.update(overrides)
    return data


def test_only_admins_can_manage_products(api, monkeypatch):
    client, _ = api
    admin = _admin(client, monkeypatch)
    user = register(client, "user@shop.com")

    assert client.post("/admin/products", json=_product()).status_code == 401
    assert client.post("/admin/products", json=_product(), headers=user).status_code == 403

    created = client.post("/admin/products", json=_product(), headers=admin)
    assert created.status_code == 201, created.text
    pid = created.json()["id"]
    assert created.json()["ingredients"] == ["Aqua", "Salicylic Acid", "Niacinamide (Vitamin B3)", "Glycerin"]

    assert client.put(f"/admin/products/{pid}", json=_product(price=999), headers=user).status_code == 403
    updated = client.put(f"/admin/products/{pid}", json=_product(price=999, stock=2), headers=admin)
    assert updated.json()["price"] == 999 and updated.json()["stock"] == 2

    assert client.delete(f"/admin/products/{pid}", headers=user).status_code == 403
    assert client.delete(f"/admin/products/{pid}", headers=admin).status_code == 204
    assert client.get(f"/products/{pid}").status_code == 404


def test_ingredient_search_match_avoid_and_filters(api, monkeypatch):
    client, _ = api
    admin = _admin(client, monkeypatch)
    client.post("/admin/products", json=_product(), headers=admin)
    client.post("/admin/products", json=_product(
        name="Calm Moisturiser", category="Moisturizer", price=800,
        ingredients="Aqua, Niacinamide, Ceramide NP, Parfum", skin_types=["Dry"], concerns=["Dry Skin"],
    ), headers=admin)
    client.post("/admin/products", json=_product(name="Hidden", is_active=False), headers=admin)

    res = client.get("/products", params={"ingredients": "niacinamide"}).json()
    assert res["total"] == 2  # inactive product is hidden
    assert all("niacinamide" in [m.lower() for m in p["matched_ingredients"]] for p in res["items"])
    assert "Sponsored" in res["ranking"] or "sponsored" in res["ranking"].lower()

    both = client.get("/products", params={"ingredients": "niacinamide,salicylic acid", "match": "all"}).json()
    assert [p["name"] for p in both["items"]] == ["Clear Skin Gel Cleanser"]

    ranked = client.get("/products", params={"ingredients": "niacinamide,salicylic acid"}).json()
    assert ranked["items"][0]["name"] == "Clear Skin Gel Cleanser"  # more matches first
    assert ranked["items"][0]["match_score"] == 1.0

    no_fragrance = client.get("/products", params={"avoid": "fragrance"}).json()
    assert [p["name"] for p in no_fragrance["items"]] == ["Clear Skin Gel Cleanser"]

    cheap = client.get("/products", params={"max_price": 900}).json()
    assert [p["name"] for p in cheap["items"]] == ["Calm Moisturiser"]

    dry = client.get("/products", params={"skin_type": "Dry"}).json()
    assert [p["name"] for p in dry["items"]] == ["Calm Moisturiser"]

    by_name = client.get("/products", params={"q": "calm"}).json()
    assert by_name["total"] == 1

    moist = client.get("/products", params={"category": "Moisturizer"}).json()["items"][0]
    assert any("fragrance" in c.lower() for c in moist["cautions"])


def test_stale_price_is_flagged(api, monkeypatch):
    client, _ = api
    admin = _admin(client, monkeypatch)
    old = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    p = client.post("/admin/products", json=_product(price_checked_at=old), headers=admin).json()
    assert p["price_is_stale"] is True
    p2 = client.post("/admin/products", json=_product(name="New", price_checked_at=None), headers=admin).json()
    assert p2["price_is_stale"] is True


def test_cart_checkout_stock_and_cancel(api, monkeypatch):
    client, SessionLocal = api
    admin = _admin(client, monkeypatch)
    pid = client.post("/admin/products", json=_product(stock=3), headers=admin).json()["id"]
    user = register(client, "buyer@shop.com")

    assert client.get("/cart").status_code == 401
    cart = client.post("/cart/items", json={"product_id": pid, "quantity": 2}, headers=user).json()
    assert cart["item_count"] == 2 and cart["subtotal"] == 2400.0 and cart["can_checkout"]

    # Quantity is capped by stock
    cart = client.post("/cart/items", json={"product_id": pid, "quantity": 5}, headers=user).json()
    assert cart["items"][0]["quantity"] == 3

    item_id = cart["items"][0]["id"]
    cart = client.patch(f"/cart/items/{item_id}", json={"quantity": 2}, headers=user).json()
    assert cart["subtotal"] == 2400.0

    shipping = {"shipping_name": "Ali Khan", "shipping_phone": "+92 300 1234567",
                "shipping_address": "House 1, Street 2", "shipping_city": "Mirpur"}
    order = client.post("/orders", json=shipping, headers=user)
    assert order.status_code == 201, order.text
    order = order.json()
    assert order["status"] == "pending" and order["payment_method"] == "cash_on_delivery"
    assert order["subtotal"] == 2400.0 and order["items"][0]["quantity"] == 2

    assert client.get("/cart", headers=user).json()["items"] == []
    assert client.get(f"/products/{pid}").json()["stock"] == 1

    # Another user cannot see or cancel it
    other = register(client, "other@shop.com")
    assert client.get(f"/orders/{order['id']}", headers=other).status_code == 404
    assert client.post(f"/orders/{order['id']}/cancel", headers=other).status_code == 404

    cancelled = client.post(f"/orders/{order['id']}/cancel", headers=user).json()
    assert cancelled["status"] == "cancelled"
    assert client.get(f"/products/{pid}").json()["stock"] == 3


def test_checkout_rejects_when_stock_runs_out(api, monkeypatch):
    client, SessionLocal = api
    admin = _admin(client, monkeypatch)
    pid = client.post("/admin/products", json=_product(stock=2), headers=admin).json()["id"]
    user = register(client, "late@shop.com")
    client.post("/cart/items", json={"product_id": pid, "quantity": 2}, headers=user)

    with SessionLocal() as db:
        db.get(Product, pid).stock = 1
        db.commit()

    shipping = {"shipping_name": "Ali Khan", "shipping_phone": "03001234567",
                "shipping_address": "House 1, Street 2", "shipping_city": "Mirpur"}
    assert client.post("/orders", json=shipping, headers=user).status_code == 409
    assert client.get(f"/products/{pid}").json()["stock"] == 1


def test_admin_order_status_transitions(api, monkeypatch):
    client, _ = api
    admin = _admin(client, monkeypatch)
    pid = client.post("/admin/products", json=_product(stock=5), headers=admin).json()["id"]
    user = register(client, "flow@shop.com")
    client.post("/cart/items", json={"product_id": pid, "quantity": 1}, headers=user)
    oid = client.post("/orders", json={"shipping_name": "Sara", "shipping_phone": "03001234567",
                                       "shipping_address": "Block A, Road 5", "shipping_city": "Lahore"},
                      headers=user).json()["id"]

    assert client.get("/admin/orders", headers=user).status_code == 403
    listing = client.get("/admin/orders", headers=admin).json()
    assert listing[0]["user_email"] == "flow@shop.com"

    assert client.patch(f"/admin/orders/{oid}", json={"status": "delivered"}, headers=admin).status_code == 409
    for st in ["confirmed", "shipped", "delivered"]:
        assert client.patch(f"/admin/orders/{oid}", json={"status": st}, headers=admin).json()["status"] == st
    assert client.post(f"/orders/{oid}/cancel", headers=user).status_code == 409


def test_deleting_product_keeps_order_history(api, monkeypatch):
    client, _ = api
    admin = _admin(client, monkeypatch)
    pid = client.post("/admin/products", json=_product(), headers=admin).json()["id"]
    user = register(client, "history@shop.com")
    client.post("/cart/items", json={"product_id": pid, "quantity": 1}, headers=user)
    client.post("/orders", json={"shipping_name": "Sara", "shipping_phone": "03001234567",
                                 "shipping_address": "Block A, Road 5", "shipping_city": "Lahore"}, headers=user)

    assert client.delete(f"/admin/products/{pid}", headers=admin).status_code == 204
    orders = client.get("/orders", headers=user).json()
    assert orders[0]["items"][0]["product_name"] == "Clear Skin Gel Cleanser"
    assert orders[0]["items"][0]["product_id"] is None


def test_product_image_upload_is_public_and_validated(api, monkeypatch):
    client, _ = api
    admin = _admin(client, monkeypatch)
    pid = client.post("/admin/products", json=_product(), headers=admin).json()["id"]

    bad = client.post(f"/admin/products/{pid}/image", headers=admin,
                      files={"file": ("x.jpg", b"not an image" * 10, "image/jpeg")})
    assert bad.status_code == 400

    ok = client.post(f"/admin/products/{pid}/image", headers=admin,
                     files={"file": ("p.jpg", to_bytes(make_skin_closeup()), "image/jpeg")})
    url = ok.json()["image_url"]
    assert url.startswith("/files/products/") and "sig=" not in url
    assert client.get(url).status_code == 200


def test_recommendations_use_latest_facial_analysis_only(api, monkeypatch):
    client, SessionLocal = api
    admin = _admin(client, monkeypatch)
    client.post("/admin/products", json=_product(), headers=admin)
    user = register(client, "rec@shop.com")

    assert client.get("/products/recommended", headers=user).json()["items"] == []

    with SessionLocal() as db:
        u = db.query(User).filter(User.email == "rec@shop.com").one()
        db.add(SkinAnalysis(user_id=u.id, predicted_condition="Acne, Visible Pores",
                            confidence_score=80, severity_level="Low", analysis_track="facial_concerns"))
        db.commit()

    rec = client.get("/products/recommended", headers=user).json()
    assert rec["based_on"] == ["Acne", "Visible Pores"]
    assert "Adapalene" not in rec["ingredients"]
    assert rec["items"][0]["name"] == "Clear Skin Gel Cleanser"
    assert rec["items"][0]["why"]

    with SessionLocal() as db:
        u = db.query(User).filter(User.email == "rec@shop.com").one()
        db.add(SkinAnalysis(user_id=u.id, predicted_condition="Features that may be consistent with Psoriasis",
                            confidence_score=80, severity_level="Moderate", analysis_track="disease_screening",
                            created_at=datetime.now(timezone.utc) + timedelta(seconds=5)))
        db.commit()

    rec = client.get("/products/recommended", headers=user).json()
    assert rec["items"] == [] and "medical" in rec["message"].lower()
