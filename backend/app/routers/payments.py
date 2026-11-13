"""Online payments API (card through Safepay or Stripe, PayPal). See services/payments.py."""

from __future__ import annotations

import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.db.models import Payment, User
from app.dependencies import get_current_user, require_admin
from app.services import payments, rate_limit

router = APIRouter(tags=["payments"])

Purpose = Literal["order", "appointment"]


class CheckoutIn(BaseModel):
    purpose: Purpose
    reference_id: str
    provider: Literal["stripe", "safepay", "paypal"]


def _http(error: payments.PaymentError) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail=error.message)


def _out(payment: Payment) -> dict:
    return {
        "id": payment.id,
        "status": payment.status,
        "purpose": payment.purpose,
        "reference_id": payment.reference_id,
        "provider": payment.provider,
        "amount": payment.amount,
        "currency": payment.currency,
        "charged_amount": payment.charged_amount,
        "charged_currency": payment.charged_currency,
        "created_at": payment.created_at,
    }


@router.get("/payments/methods")
def payment_methods(
    purpose: Purpose = Query(...),
    reference_id: str = Query(..., max_length=64),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        payable = payments.find_payable(db, current_user, purpose, reference_id)
    except payments.PaymentError as error:
        raise _http(error) from None
    return {
        "amount": payable.amount,
        "currency": payable.currency,
        "description": payable.description,
        "methods": payments.methods(payable.amount, payable.currency),
    }


@router.post("/payments/checkout", status_code=status.HTTP_201_CREATED)
def start_checkout(
    payload: CheckoutIn,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a checkout and return the provider page the browser must open."""
    rate_limit.enforce(
        db, "checkout", current_user.id, settings.payment_checkouts_per_hour,
        message="Too many payment attempts. Please wait a while.",
    )
    try:
        payment, redirect_url = payments.start_checkout(
            db, current_user, payload.purpose, payload.reference_id, payload.provider,
            api_base=str(request.base_url),
        )
    except payments.PaymentError as error:
        raise _http(error) from None
    return {"payment": _out(payment), "redirect_url": redirect_url}


def _own_payment(db: Session, user: User, payment_id: str) -> Payment:
    payment = db.get(Payment, payment_id)
    if payment is None or payment.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found.")
    return payment


@router.post("/payments/{payment_id}/confirm")
def confirm_payment(
    payment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Called when the customer returns from the provider. The provider is asked for the result."""
    payment = _own_payment(db, current_user, payment_id)
    rate_limit.enforce(db, "payment_confirm", current_user.id, 60)
    try:
        payments.confirm(db, payment)
    except payments.PaymentError as error:
        raise _http(error) from None
    return _out(payment)


@router.post("/payments/{payment_id}/cancel")
def cancel_payment(
    payment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payment = _own_payment(db, current_user, payment_id)
    if payment.status == "created":
        payment.status = "cancelled"
        db.commit()
    return _out(payment)


@router.post("/payments/stripe/webhook", include_in_schema=False)
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Stripe calls this URL. Authenticated by the Stripe-Signature header, not by a session."""
    payload = await request.body()
    try:
        result = payments.handle_stripe_webhook(db, payload, request.headers.get("stripe-signature", ""))
    except payments.PaymentError as error:
        raise _http(error) from None
    return {"received": True, "result": result}


@router.api_route("/payments/safepay/return", methods=["GET", "POST"], include_in_schema=False)
def safepay_return(payment: str = Query("", max_length=64), cancelled: str = Query("", max_length=1)):
    """
    Safepay sends the customer's browser here after the payment page. Nothing
    is decided here: the browser is forwarded to the web app, which asks the
    server to check the payment. The target is always this site's own page.
    """
    if not re.fullmatch(r"[A-Za-z0-9-]{1,64}", payment):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found.")
    target = f"{settings.frontend_url.rstrip('/')}/payment/return?payment={payment}"
    if cancelled == "1":
        target += "&cancelled=1"
    return RedirectResponse(target, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/payments/safepay/webhook", include_in_schema=False)
async def safepay_webhook(request: Request, db: Session = Depends(get_db)):
    """Safepay calls this URL. Authenticated by the X-SFPY-SIGNATURE header, not by a session."""
    payload = await request.body()
    try:
        result = payments.handle_safepay_webhook(db, payload, request.headers.get("x-sfpy-signature", ""))
    except payments.PaymentError as error:
        raise _http(error) from None
    return {"received": True, "result": result}


@router.get("/admin/payments")
def admin_list_payments(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rows = db.query(Payment).order_by(desc(Payment.created_at)).limit(300).all()
    emails = dict(db.query(User.id, User.email).filter(User.id.in_({p.user_id for p in rows})).all()) if rows else {}
    return [{**_out(p), "user_email": emails.get(p.user_id)} for p in rows]
