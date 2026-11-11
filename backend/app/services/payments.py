"""
Online payments: card (Stripe Checkout) and PayPal.

The customer always pays on the provider's own page. Card numbers never
reach this server, so it stays outside most of PCI DSS. This module only

1. asks the provider to create a checkout for an exact amount,
2. sends the browser there, and
3. afterwards asks the provider (server to server) whether that checkout
   was paid, and marks the order or appointment as paid.

Nothing the browser says is trusted for step 3. A Stripe webhook does the
same when the customer closes the tab before returning.

Without API keys a provider is reported as "not set up" and cannot be
chosen. Cash on delivery / pay at the clinic keep working.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
from dataclasses import dataclass
from urllib.parse import quote

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Appointment, Order, Payment, User
from app.services import automation, http_client

logger = logging.getLogger("skyntri.payments")

STRIPE_API = "https://api.stripe.com/v1"
PAYPAL_API = {"live": "https://api-m.paypal.com", "sandbox": "https://api-m.sandbox.paypal.com"}
STRIPE_ZERO_DECIMAL = {"bif", "clp", "djf", "gnf", "jpy", "kmf", "krw", "mga", "pyg", "rwf", "ugx", "vnd", "vuv",
                       "xaf", "xof", "xpf"}
WEBHOOK_TOLERANCE_SECONDS = 300
PROVIDERS = ("stripe", "paypal")
METHOD_NAME = {"stripe": "card", "paypal": "paypal"}


class PaymentError(Exception):
    """A problem the customer can be told about."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass
class Payable:
    purpose: str
    reference_id: str
    amount: float
    currency: str
    description: str
    target: Order | Appointment


# ============================================================
# What can be paid, and how
# ============================================================

def find_payable(db: Session, user: User, purpose: str, reference_id: str) -> Payable:
    if purpose == "order":
        order = db.get(Order, reference_id)
        if order is None or order.user_id != user.id:
            raise PaymentError("Order not found.", 404)
        if order.status == "cancelled":
            raise PaymentError("This order was cancelled.", 409)
        if (order.payment_status or "unpaid") != "unpaid":
            raise PaymentError("This order is already paid.", 409)
        return Payable("order", order.id, round(order.subtotal, 2), order.currency,
                       f"{settings.clinic_name} order {order.id[:8]}", order)

    if purpose == "appointment":
        appointment = db.get(Appointment, reference_id)
        if appointment is None or appointment.patient_id != user.id:
            raise PaymentError("Appointment not found.", 404)
        if appointment.status not in {"requested", "confirmed"}:
            raise PaymentError(f"A {appointment.status} appointment cannot be paid.", 409)
        if appointment.payment_status != "unpaid" or (appointment.fee or 0) <= 0:
            raise PaymentError("There is nothing to pay for this appointment.", 409)
        return Payable("appointment", appointment.id, round(appointment.fee, 2), appointment.currency,
                       f"Consultation with {appointment.doctor.user.full_name}", appointment)

    raise PaymentError("Unknown payment type.")


def paypal_amount(amount: float, currency: str) -> tuple[float, str] | None:
    """What PayPal would charge, or None when the currency cannot be converted."""
    target = settings.paypal_currency.strip().upper() or "USD"
    if currency.upper() == target:
        return round(amount, 2), target
    if settings.paypal_exchange_rate and settings.paypal_exchange_rate > 0:
        return round(amount / settings.paypal_exchange_rate, 2), target
    return None


def methods(amount: float, currency: str) -> list[dict]:
    converted = paypal_amount(amount, currency)
    paypal_note = None
    if not settings.paypal_configured:
        paypal_note = "PayPal is not set up yet."
    elif converted is None:
        paypal_note = f"PayPal cannot charge {currency}. An exchange rate has not been set."
    elif converted[0] < 0.01:
        paypal_note = "The amount is too small for PayPal."

    return [
        {
            "id": "stripe",
            "label": "Card",
            "available": settings.stripe_configured,
            "note": None if settings.stripe_configured else "Card payments are not set up yet.",
            "amount": round(amount, 2),
            "currency": currency,
            "test_mode": settings.stripe_secret_key.startswith("sk_test_"),
        },
        {
            "id": "paypal",
            "label": "PayPal",
            "available": paypal_note is None,
            "note": paypal_note,
            "amount": converted[0] if converted else None,
            "currency": converted[1] if converted else None,
            "test_mode": settings.paypal_mode.strip().lower() != "live",
        },
    ]


# ============================================================
# Stripe
# ============================================================

def _stripe(method: str, path: str, form: dict | None = None) -> dict:
    try:
        response = http_client.send(
            method, STRIPE_API + path, form=form, timeout=20,
            headers={"Authorization": f"Bearer {settings.stripe_secret_key}"},
        )
        data = response.json()
    except http_client.HttpError:
        raise PaymentError("The card payment service could not be reached. Please try again.", 502) from None
    if not response.ok:
        logger.warning("stripe_error", extra={"event": "stripe_error", "status": response.status,
                                              "code": (data.get("error") or {}).get("code")})
        raise PaymentError("The card payment could not be started. Please try another method.", 502)
    return data


def _minor_units(amount: float, currency: str) -> int:
    return int(round(amount)) if currency.lower() in STRIPE_ZERO_DECIMAL else int(round(amount * 100))


def _stripe_create(payment: Payment, payable: Payable, user: User, return_url: str) -> tuple[str, str]:
    session = _stripe("POST", "/checkout/sessions", {
        "mode": "payment",
        "success_url": return_url,
        "cancel_url": return_url + "&cancelled=1",
        "client_reference_id": payment.id,
        "customer_email": user.email,
        "metadata[payment_id]": payment.id,
        "line_items[0][quantity]": "1",
        "line_items[0][price_data][currency]": payment.charged_currency.lower(),
        "line_items[0][price_data][unit_amount]": str(_minor_units(payment.charged_amount, payment.charged_currency)),
        "line_items[0][price_data][product_data][name]": payable.description[:120],
    })
    return session["id"], session["url"]


def _stripe_is_paid(payment: Payment, session: dict | None = None) -> bool:
    session = session or _stripe("GET", f"/checkout/sessions/{quote(payment.provider_ref or '', safe='')}")
    expected = _minor_units(payment.charged_amount, payment.charged_currency)
    return (
        session.get("id") == payment.provider_ref
        and session.get("payment_status") == "paid"
        and session.get("client_reference_id") == payment.id
        and int(session.get("amount_total") or -1) == expected
        and str(session.get("currency") or "").lower() == payment.charged_currency.lower()
    )


def verify_stripe_signature(payload: bytes, header: str, secret: str, now: float | None = None) -> bool:
    """Stripe-Signature: t=<unix time>,v1=<hex hmac of "t.payload">[,v1=...]"""
    parts = [p.split("=", 1) for p in (header or "").split(",") if "=" in p]
    timestamp = next((v for k, v in parts if k.strip() == "t"), "")
    signatures = [v for k, v in parts if k.strip() == "v1"]
    if not timestamp.isdigit() or not signatures or not secret:
        return False
    if abs((now or time.time()) - int(timestamp)) > WEBHOOK_TOLERANCE_SECONDS:
        return False
    expected = hmac.new(secret.encode(), timestamp.encode() + b"." + payload, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, s) for s in signatures)


def handle_stripe_webhook(db: Session, payload: bytes, signature: str) -> str:
    if not settings.stripe_webhook_secret:
        raise PaymentError("Webhook is not configured.", 503)
    if not verify_stripe_signature(payload, signature, settings.stripe_webhook_secret):
        raise PaymentError("Invalid signature.", 400)

    try:
        event = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise PaymentError("Invalid payload.", 400) from None

    if event.get("type") not in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
        return "ignored"

    session = (event.get("data") or {}).get("object") or {}
    payment = db.query(Payment).filter(
        Payment.provider == "stripe", Payment.provider_ref == session.get("id")
    ).first()
    if payment is None:
        return "unknown"
    # Ask Stripe again instead of trusting the event body for the amount.
    if payment.status != "succeeded" and _stripe_is_paid(payment):
        mark_paid(db, payment)
    return payment.status


# ============================================================
# PayPal
# ============================================================

def _paypal_base() -> str:
    return PAYPAL_API["live" if settings.paypal_mode.strip().lower() == "live" else "sandbox"]


def _paypal_token() -> str:
    credentials = base64.b64encode(
        f"{settings.paypal_client_id}:{settings.paypal_client_secret}".encode()
    ).decode()
    try:
        response = http_client.send(
            "POST", _paypal_base() + "/v1/oauth2/token", form={"grant_type": "client_credentials"},
            headers={"Authorization": f"Basic {credentials}"}, timeout=20,
        )
        token = response.json().get("access_token") if response.ok else None
    except http_client.HttpError:
        token = None
    if not token:
        raise PaymentError("PayPal could not be reached. Please try again.", 502)
    return token


def _paypal(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    try:
        response = http_client.send(
            method, _paypal_base() + path, json_body=body if body is not None else ({} if method == "POST" else None),
            headers={"Authorization": f"Bearer {_paypal_token()}"}, timeout=20,
        )
        return response.status, response.json()
    except http_client.HttpError:
        raise PaymentError("PayPal could not be reached. Please try again.", 502) from None


def _paypal_create(payment: Payment, payable: Payable, return_url: str) -> tuple[str, str]:
    status_code, order = _paypal("POST", "/v2/checkout/orders", {
        "intent": "CAPTURE",
        "purchase_units": [{
            "reference_id": payment.id,
            "custom_id": payment.id,
            "description": payable.description[:120],
            "amount": {"currency_code": payment.charged_currency, "value": f"{payment.charged_amount:.2f}"},
        }],
        "payment_source": {"paypal": {"experience_context": {
            "brand_name": settings.clinic_name[:120],
            "user_action": "PAY_NOW",
            "shipping_preference": "NO_SHIPPING",
            "return_url": return_url,
            "cancel_url": return_url + "&cancelled=1",
        }}},
    })
    approve = next((link.get("href") for link in order.get("links", [])
                    if link.get("rel") in {"payer-action", "approve"}), None)
    if status_code not in (200, 201) or not order.get("id") or not approve:
        logger.warning("paypal_error", extra={"event": "paypal_error", "status": status_code})
        raise PaymentError("The PayPal payment could not be started. Please try another method.", 502)
    return order["id"], approve


def _paypal_capture_is_complete(payment: Payment) -> bool:
    ref = quote(payment.provider_ref or "", safe="")
    status_code, order = _paypal("POST", f"/v2/checkout/orders/{ref}/capture")
    if status_code == 422:  # e.g. already captured: read the current state
        status_code, order = _paypal("GET", f"/v2/checkout/orders/{ref}")
    if status_code not in (200, 201) or order.get("status") != "COMPLETED":
        return False

    unit = (order.get("purchase_units") or [{}])[0]
    captures = ((unit.get("payments") or {}).get("captures")) or []
    capture = captures[0] if captures else {}
    amount = capture.get("amount") or unit.get("amount") or {}
    try:
        value = round(float(amount.get("value")), 2)
    except (TypeError, ValueError):
        return False
    return (
        order.get("id") == payment.provider_ref
        and (unit.get("reference_id") == payment.id or capture.get("custom_id") == payment.id)
        and capture.get("status", "COMPLETED") == "COMPLETED"
        and value == round(payment.charged_amount, 2)
        and str(amount.get("currency_code", "")).upper() == payment.charged_currency.upper()
    )


# ============================================================
# Checkout flow
# ============================================================

def start_checkout(db: Session, user: User, purpose: str, reference_id: str, provider: str) -> tuple[Payment, str]:
    if provider not in PROVIDERS:
        raise PaymentError("Unknown payment method.")
    payable = find_payable(db, user, purpose, reference_id)

    method = next(m for m in methods(payable.amount, payable.currency) if m["id"] == provider)
    if not method["available"]:
        raise PaymentError(method["note"] or "This payment method is not available.", 409)

    payment = Payment(
        user_id=user.id, purpose=purpose, reference_id=reference_id, provider=provider,
        amount=payable.amount, currency=payable.currency,
        charged_amount=method["amount"], charged_currency=method["currency"], status="created",
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    return_url = f"{settings.frontend_url.rstrip('/')}/payment/return?payment={payment.id}"
    try:
        if provider == "stripe":
            payment.provider_ref, redirect = _stripe_create(payment, payable, user, return_url)
        else:
            payment.provider_ref, redirect = _paypal_create(payment, payable, return_url)
    except PaymentError:
        payment.status = "failed"
        db.commit()
        raise
    db.commit()
    return payment, redirect


def mark_paid(db: Session, payment: Payment) -> None:
    """Idempotent: safe when the return page and the webhook both arrive."""
    if payment.status == "succeeded":
        return
    payment.status = "succeeded"

    target: Order | Appointment | None
    target = db.get(Order if payment.purpose == "order" else Appointment, payment.reference_id)
    if target is not None and (target.payment_status or "unpaid") == "unpaid":
        target.payment_status = "paid"
        target.payment_method = METHOD_NAME[payment.provider]
    db.commit()

    automation.emit(db, "payment.succeeded", {
        "payment_id": payment.id, "purpose": payment.purpose, "reference_id": payment.reference_id,
        "provider": payment.provider, "amount": payment.amount, "currency": payment.currency,
        "charged_amount": payment.charged_amount, "charged_currency": payment.charged_currency,
    })


def confirm(db: Session, payment: Payment) -> Payment:
    """Ask the provider whether this checkout was paid."""
    if payment.status in {"succeeded", "refunded"} or not payment.provider_ref:
        return payment
    paid = _stripe_is_paid(payment) if payment.provider == "stripe" else _paypal_capture_is_complete(payment)
    if paid:
        mark_paid(db, payment)
    return payment
