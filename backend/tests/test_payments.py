"""Online payments with fake Stripe / PayPal servers (no network, no money)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qs

import pytest

from app.core.config import settings
from app.services import http_client, payments
from tests.conftest import register
from tests.test_shop import _product

SHIPPING = {"shipping_name": "Sara", "shipping_phone": "03001234567",
            "shipping_address": "Block A, Road 5", "shipping_city": "Lahore"}


class FakeProviders:
    """Stands in for api.stripe.com and api-m.sandbox.paypal.com."""

    def __init__(self):
        self.stripe_sessions: dict[str, dict] = {}
        self.paypal_orders: dict[str, dict] = {}
        self.calls: list[tuple[str, str]] = []

    def send(self, method, url, *, headers=None, json_body=None, form=None, data=None, timeout=15.0):
        self.calls.append((method, url))
        reply = lambda status, body: http_client.HttpResponse(status, json.dumps(body).encode())  # noqa: E731

        if url.startswith("https://api.stripe.com/v1/checkout/sessions"):
            assert headers["Authorization"] == "Bearer sk_test_abc"
            if method == "POST":
                sid = f"cs_test_{len(self.stripe_sessions) + 1}"
                self.stripe_sessions[sid] = {
                    "id": sid, "url": f"https://checkout.stripe.com/c/pay/{sid}", "payment_status": "unpaid",
                    "client_reference_id": form["client_reference_id"],
                    "amount_total": int(form["line_items[0][price_data][unit_amount]"]),
                    "currency": form["line_items[0][price_data][currency]"],
                    "success_url": form["success_url"],
                }
                return reply(200, self.stripe_sessions[sid])
            return reply(200, self.stripe_sessions[url.rsplit("/", 1)[1]])

        if url.endswith("/v1/oauth2/token"):
            assert headers["Authorization"].startswith("Basic ")
            return reply(200, {"access_token": "paypal-token"})

        if "/v2/checkout/orders" in url:
            assert url.startswith("https://api-m.sandbox.paypal.com") and headers["Authorization"] == "Bearer paypal-token"
            if method == "POST" and url.endswith("/v2/checkout/orders"):
                oid = f"PP{len(self.paypal_orders) + 1}"
                unit = json_body["purchase_units"][0]
                self.paypal_orders[oid] = {"id": oid, "status": "CREATED", "approved": False, "unit": unit}
                return reply(201, {"id": oid, "status": "PAYER_ACTION_REQUIRED", "links": [
                    {"rel": "payer-action", "href": f"https://www.sandbox.paypal.com/checkoutnow?token={oid}"}]})
            oid = url.split("/v2/checkout/orders/")[1].split("/")[0]
            order = self.paypal_orders[oid]
            if url.endswith("/capture"):
                if not order["approved"]:
                    return reply(422, {"name": "UNPROCESSABLE_ENTITY", "details": [{"issue": "ORDER_NOT_APPROVED"}]})
                order["status"] = "COMPLETED"
            return reply(200, {"id": oid, "status": order["status"], "purchase_units": [{
                "reference_id": order["unit"]["reference_id"],
                "payments": {"captures": [{"status": "COMPLETED", "custom_id": order["unit"]["custom_id"],
                                           "amount": order["unit"]["amount"]}]} if order["status"] == "COMPLETED" else {},
                "amount": order["unit"]["amount"]}]})

        raise AssertionError(f"unexpected request {method} {url}")


@pytest.fixture
def shop(api, monkeypatch):
    client, SessionLocal = api
    fake = FakeProviders()
    monkeypatch.setattr(http_client, "send", fake.send)
    monkeypatch.setattr(settings, "admin_emails", "boss@test.com")
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_abc")
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test")
    monkeypatch.setattr(settings, "paypal_client_id", "pp-id")
    monkeypatch.setattr(settings, "paypal_client_secret", "pp-secret")
    monkeypatch.setattr(settings, "paypal_exchange_rate", 280.0)
    admin = register(client, "boss@test.com")
    product_id = client.post("/admin/products", json=_product(stock=5), headers=admin).json()["id"]
    buyer = register(client, "buyer@test.com")
    client.post("/cart/items", json={"product_id": product_id, "quantity": 2}, headers=buyer)
    order = client.post("/orders", json=SHIPPING, headers=buyer).json()
    return client, fake, admin, buyer, order


def _checkout(client, headers, order, provider):
    return client.post("/payments/checkout", headers=headers,
                       json={"purpose": "order", "reference_id": order["id"], "provider": provider})


def _order(client, headers, order):
    return next(o for o in client.get("/orders", headers=headers).json() if o["id"] == order["id"])


def test_methods_report_what_is_set_up(shop, monkeypatch):
    client, _, _, buyer, order = shop
    params = {"purpose": "order", "reference_id": order["id"]}
    info = client.get("/payments/methods", params=params, headers=buyer).json()
    card, paypal = info["methods"]
    assert info["amount"] == 2400.0 and info["currency"] == "PKR"
    assert card["available"] and card["test_mode"] and card["amount"] == 2400.0
    assert paypal["available"] and (paypal["amount"], paypal["currency"]) == (8.57, "USD")  # 2400 / 280

    monkeypatch.setattr(settings, "stripe_secret_key", "")
    monkeypatch.setattr(settings, "paypal_exchange_rate", 0.0)
    card, paypal = client.get("/payments/methods", params=params, headers=buyer).json()["methods"]
    assert not card["available"] and "not set up" in card["note"]
    assert not paypal["available"] and "exchange rate" in paypal["note"]
    assert _checkout(client, buyer, order, "stripe").status_code == 409
    assert _checkout(client, buyer, order, "paypal").status_code == 409


def test_card_payment_is_confirmed_with_stripe_not_with_the_browser(shop):
    client, fake, admin, buyer, order = shop
    started = _checkout(client, buyer, order, "stripe")
    assert started.status_code == 201, started.text
    payment = started.json()["payment"]
    session_id, session = next(iter(fake.stripe_sessions.items()))
    assert started.json()["redirect_url"] == f"https://checkout.stripe.com/c/pay/{session_id}"
    assert session["amount_total"] == 240000 and session["currency"] == "pkr"  # minor units
    assert session["success_url"].startswith(f"{settings.frontend_url}/payment/return?payment={payment['id']}")

    # Returning without paying changes nothing.
    assert client.post(f"/payments/{payment['id']}/confirm", headers=buyer).json()["status"] == "created"
    assert _order(client, buyer, order)["payment_status"] == "unpaid"

    # A paid session for a different amount is not accepted either.
    session.update(payment_status="paid", amount_total=100)
    assert client.post(f"/payments/{payment['id']}/confirm", headers=buyer).json()["status"] == "created"

    session.update(amount_total=240000)
    assert client.post(f"/payments/{payment['id']}/confirm", headers=buyer).json()["status"] == "succeeded"
    paid = _order(client, buyer, order)
    assert paid["payment_status"] == "paid" and paid["payment_method"] == "card"

    # Idempotent, and a paid order cannot be paid twice.
    assert client.post(f"/payments/{payment['id']}/confirm", headers=buyer).json()["status"] == "succeeded"
    assert _checkout(client, buyer, order, "stripe").status_code == 409
    listed = client.get("/admin/payments", headers=admin).json()
    assert listed[0]["status"] == "succeeded" and listed[0]["user_email"] == "buyer@test.com"
    assert client.get("/admin/payments", headers=buyer).status_code == 403


def test_payments_belong_to_their_owner(shop):
    client, fake, _, buyer, order = shop
    stranger = register(client, "stranger@test.com")
    assert _checkout(client, stranger, order, "stripe").status_code == 404
    assert client.get("/payments/methods", params={"purpose": "order", "reference_id": order["id"]},
                      headers=stranger).status_code == 404
    payment_id = _checkout(client, buyer, order, "stripe").json()["payment"]["id"]
    next(iter(fake.stripe_sessions.values()))["payment_status"] = "paid"
    assert client.post(f"/payments/{payment_id}/confirm", headers=stranger).status_code == 404
    assert client.post(f"/payments/{payment_id}/cancel", headers=stranger).status_code == 404
    assert client.post(f"/payments/{payment_id}/confirm").status_code == 401
    assert _order(client, buyer, order)["payment_status"] == "unpaid"


def _signed(body: bytes, secret="whsec_test", timestamp=None):
    timestamp = str(int(timestamp or time.time()))
    digest = hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
    return {"stripe-signature": f"t={timestamp},v1={digest}", "content-type": "application/json"}


def test_stripe_webhook_needs_a_valid_signature(shop):
    client, fake, _, buyer, order = shop
    _checkout(client, buyer, order, "stripe")
    session_id, session = next(iter(fake.stripe_sessions.items()))
    body = json.dumps({"type": "checkout.session.completed",
                       "data": {"object": {"id": session_id, "payment_status": "paid"}}}).encode()
    url = "/payments/stripe/webhook"

    assert client.post(url, content=body, headers={"content-type": "application/json"}).status_code == 400
    assert client.post(url, content=body, headers=_signed(body, secret="wrong")).status_code == 400
    assert client.post(url, content=body, headers=_signed(body, timestamp=time.time() - 3600)).status_code == 400
    assert client.post(url, content=body + b" ", headers=_signed(body)).status_code == 400

    # Signed event, but Stripe itself says the session is not paid: nothing happens.
    assert client.post(url, content=body, headers=_signed(body)).json()["result"] == "created"
    assert _order(client, buyer, order)["payment_status"] == "unpaid"

    session["payment_status"] = "paid"
    assert client.post(url, content=body, headers=_signed(body)).json()["result"] == "succeeded"
    assert _order(client, buyer, order)["payment_status"] == "paid"

    other = json.dumps({"type": "customer.created", "data": {"object": {}}}).encode()
    assert client.post(url, content=other, headers=_signed(other)).json()["result"] == "ignored"


def test_paypal_payment_is_captured_after_approval(shop):
    client, fake, _, buyer, order = shop
    started = _checkout(client, buyer, order, "paypal")
    assert started.status_code == 201, started.text
    payment = started.json()["payment"]
    order_id, paypal_order = next(iter(fake.paypal_orders.items()))
    assert parse_qs(started.json()["redirect_url"].split("?")[1])["token"] == [order_id]
    assert paypal_order["unit"]["amount"] == {"currency_code": "USD", "value": "8.57"}
    assert (payment["charged_amount"], payment["charged_currency"]) == (8.57, "USD")

    # Not approved on PayPal yet.
    assert client.post(f"/payments/{payment['id']}/confirm", headers=buyer).json()["status"] == "created"
    paypal_order["approved"] = True
    assert client.post(f"/payments/{payment['id']}/confirm", headers=buyer).json()["status"] == "succeeded"
    paid = _order(client, buyer, order)
    assert paid["payment_status"] == "paid" and paid["payment_method"] == "paypal"


def test_appointment_fee_can_be_paid_online(shop):
    from tests.test_clinic import _book, _doctor

    client, fake, admin, buyer, _ = shop
    _, doctor_id = _doctor(client, admin)
    appointment = _book(client, buyer, doctor_id).json()

    started = client.post("/payments/checkout", headers=buyer, json={
        "purpose": "appointment", "reference_id": appointment["id"], "provider": "stripe"})
    assert started.status_code == 201, started.text
    session = list(fake.stripe_sessions.values())[-1]
    assert session["amount_total"] == 250000
    session["payment_status"] = "paid"
    client.post(f"/payments/{started.json()['payment']['id']}/confirm", headers=buyer)

    seen = client.get(f"/appointments/{appointment['id']}", headers=buyer).json()
    assert seen["payment_status"] == "paid" and seen["payment_method"] == "card"
    again = client.post("/payments/checkout", headers=buyer, json={
        "purpose": "appointment", "reference_id": appointment["id"], "provider": "stripe"})
    assert again.status_code == 409


def test_provider_outage_is_reported_cleanly(shop, monkeypatch):
    client, _, _, buyer, order = shop

    def down(*args, **kwargs):
        raise http_client.HttpError("boom")

    monkeypatch.setattr(http_client, "send", down)
    failed = _checkout(client, buyer, order, "stripe")
    assert failed.status_code == 502 and "sk_test" not in failed.text
    assert _order(client, buyer, order)["payment_status"] == "unpaid"


def test_signature_helper_rejects_malformed_headers():
    assert not payments.verify_stripe_signature(b"{}", "", "secret")
    assert not payments.verify_stripe_signature(b"{}", "t=abc,v1=00", "secret")
    assert not payments.verify_stripe_signature(b"{}", "v1=00", "secret")
