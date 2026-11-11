"""
Built-in agents. Each one does a routine clinic job on a schedule, records
what it did (agent_runs) and tells the automation webhooks.

daily_report            Yesterday in numbers: new patients, analyses,
                        appointments, orders and payments.
appointment_reminders   Reminds patients of confirmed appointments in the
                        next 24 hours (e-mail when SMTP is set up, and an
                        "appointment.reminder" event for WhatsApp / SMS
                        workflows).
daily_post              Writes a short skin-care post about what patients
                        asked about most this week.

They are started by the in-process scheduler (AGENTS_SCHEDULER_ENABLED),
by an administrator, or by an external scheduler such as n8n through
POST /automation/v1/agents/<name>/run.

Only totals are used and sent. No agent reads a patient's photos, visit
reasons, assessments or prescriptions.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime, time, timedelta, timezone
from email.message import EmailMessage

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import AgentRun, Appointment, ClinicPost, Order, Payment, SkinAnalysis, User
from app.services import app_settings, automation, clinic, llm
from app.services.clinic import as_utc, clinic_tz, now_utc
from app.services.email import EmailDeliveryError, _send

logger = logging.getLogger("skyntri.agents")

NOT_A_CONCERN = ("no specific", "no supported", "no visible", "normal")


# ============================================================
# Daily report
# ============================================================

def _top_concerns(db: Session, since: datetime, limit: int = 5) -> list[dict]:
    counts: Counter[str] = Counter()
    rows = db.query(SkinAnalysis.predicted_condition).filter(SkinAnalysis.created_at >= since).limit(5000).all()
    for (value,) in rows:
        for label in (value or "").split(","):
            label = label.strip()
            if label and not label.lower().startswith(NOT_A_CONCERN):
                counts[label] += 1
    return [{"label": label, "count": count} for label, count in counts.most_common(limit)]


def daily_report(db: Session) -> tuple[str, dict]:
    tz = clinic_tz()
    today = datetime.now(tz).date()
    day = today - timedelta(days=1)
    start = datetime.combine(day, time.min, tzinfo=tz).astimezone(timezone.utc)
    end = start + timedelta(days=1)

    def count(model, column, *extra):
        return db.query(func.count(model.id)).filter(column >= start, column < end, *extra).scalar() or 0

    by_status = dict(
        db.query(Appointment.status, func.count(Appointment.id))
        .filter(Appointment.starts_at >= start, Appointment.starts_at < end)
        .group_by(Appointment.status)
        .all()
    )
    revenue = dict(
        db.query(Payment.currency, func.coalesce(func.sum(Payment.amount), 0.0))
        .filter(Payment.status == "succeeded", Payment.updated_at >= start, Payment.updated_at < end)
        .group_by(Payment.currency)
        .all()
    )

    details = {
        "date": day.isoformat(),
        "timezone": settings.clinic_timezone,
        "new_patients": count(User, User.created_at),
        "skin_analyses": count(SkinAnalysis, SkinAnalysis.created_at),
        "top_concerns": _top_concerns(db, start - timedelta(days=6)),
        "appointments_booked": count(Appointment, Appointment.created_at),
        "appointments_held": {k: int(v) for k, v in by_status.items()},
        "appointments_today": db.query(func.count(Appointment.id))
        .filter(Appointment.starts_at >= end, Appointment.starts_at < end + timedelta(days=1),
                Appointment.status.in_(clinic.ACTIVE_STATUSES)).scalar() or 0,
        "orders": count(Order, Order.created_at),
        "online_payments": {k: round(float(v), 2) for k, v in revenue.items()},
    }
    summary = (
        f"{day:%d %b %Y}: {details['new_patients']} new patient(s), {details['skin_analyses']} skin "
        f"analysis/analyses, {details['appointments_booked']} appointment(s) booked, "
        f"{details['orders']} order(s). Today: {details['appointments_today']} appointment(s)."
    )
    automation.emit(db, "report.daily", {**details, "summary": summary})
    return summary, details


# ============================================================
# Appointment reminders
# ============================================================

def _reminder_email(appointment: Appointment) -> bool:
    if not settings.smtp_configured:
        return False
    when = as_utc(appointment.starts_at).astimezone(clinic_tz())
    patient = appointment.patient
    message = EmailMessage()
    message["Subject"] = f"Reminder: your appointment on {when:%d %b at %H:%M}"
    message["From"] = settings.smtp_from
    message["To"] = patient.email
    message.set_content(
        f"Hello {patient.full_name or 'there'},\n\n"
        f"This is a reminder of your appointment with {appointment.doctor.user.full_name} on "
        f"{when:%A, %d %B %Y at %H:%M} ({settings.clinic_timezone}).\n\n"
        f"Open your appointment: {settings.frontend_url.rstrip('/')}/appointments/{appointment.id}\n\n"
        f"If you cannot come, please cancel it there so someone else can use the time.\n\n- {settings.clinic_name}"
    )
    try:
        _send(message)
        return True
    except EmailDeliveryError:
        logger.error("reminder_email_failed", extra={"event": "reminder_email_failed"})
        return False


def appointment_reminders(db: Session) -> tuple[str, dict]:
    now = now_utc()
    due = (
        db.query(Appointment)
        .filter(
            Appointment.status == "confirmed",
            Appointment.reminder_sent_at.is_(None),
            Appointment.starts_at > now,
            Appointment.starts_at <= now + timedelta(hours=24),
        )
        .order_by(Appointment.starts_at)
        .limit(200)
        .all()
    )

    emailed = 0
    for appointment in due:
        if _reminder_email(appointment):
            emailed += 1
        appointment.reminder_sent_at = now
        db.commit()
        data, contact = clinic.event_data(appointment)
        automation.emit(db, "appointment.reminder", data, contact)

    return f"{len(due)} reminder(s) sent, {emailed} by e-mail.", {"reminders": len(due), "emailed": emailed}


# ============================================================
# Daily post
# ============================================================

# topic keyword -> (title, body). Plain, safe skin-care basics.
TIPS: list[tuple[tuple[str, ...], str, str]] = [
    (("acne", "pimple"), "Three habits that help acne-prone skin",
     "Wash your face twice a day with a gentle cleanser, not more: over-washing irritates skin and can make "
     "breakouts worse. Do not squeeze spots, because that pushes inflammation deeper and leaves marks. "
     "Give any new product six to eight weeks before judging it. If acne is painful, leaves scars or does "
     "not improve, book a visit with a dermatologist."),
    (("blackhead", "whitehead", "pore"), "Blackheads and pores: what actually helps",
     "Blackheads are oil and dead skin in the pore that turned dark in the air, not dirt. Scrubbing harder "
     "does not remove them. A leave-on product with salicylic acid a few evenings a week, a light "
     "moisturiser and sunscreen in the morning work better than strips or harsh scrubs."),
    (("dark spot", "pigment"), "Dark spots fade slowly, and sunscreen decides how slowly",
     "Marks left by spots or sun usually fade over months. The most useful step is a broad-spectrum "
     "sunscreen of SPF 30 or more every morning, even indoors near windows, because light keeps "
     "pigment active. Avoid picking, and be careful with home remedies such as lemon juice, which can "
     "burn the skin."),
    (("wrinkle", "fine line"), "Fine lines: start with the simple things",
     "Daily sunscreen prevents more lines than any cream repairs. Add a moisturiser at night and enough "
     "sleep and water. Products with retinoids can help but may irritate at first: start two nights a "
     "week and ask a doctor first if you are pregnant or breastfeeding."),
    (("redness", "sensitive"), "Calming skin that turns red easily",
     "Use lukewarm water, a fragrance-free cleanser and a plain moisturiser. Introduce only one new "
     "product at a time, so you know what caused a reaction. Hot drinks, spicy food and sun can trigger "
     "flushing in some people. Redness that stays, or comes with burning, deserves a doctor's look."),
    (("eczema", "dry", "dermatitis"), "Dry, itchy skin needs moisture more than anything",
     "Moisturise within a few minutes after bathing, while the skin is still slightly damp, and again "
     "during the day. Keep showers short and lukewarm, and choose soap-free cleansers. If the skin "
     "cracks, weeps or keeps you awake at night, see a dermatologist."),
]
DEFAULT_TIP = (
    "The three steps every routine needs",
    "A good routine can be short: a gentle cleanser, a moisturiser that suits your skin, and a "
    "broad-spectrum sunscreen of SPF 30 or more every morning. Add other products one at a time and "
    "give each a few weeks. More steps do not mean better skin.",
)
POST_FOOTER = "\n\nThis is general information, not a diagnosis. For a personal plan, book a consultation."


def _tip_for(topic: str | None) -> tuple[str, str]:
    lowered = (topic or "").lower()
    for keywords, title, body in TIPS:
        if any(k in lowered for k in keywords):
            return title, body
    return DEFAULT_TIP


def daily_post(db: Session) -> tuple[str, dict]:
    week_ago = now_utc() - timedelta(days=7)
    concerns = _top_concerns(db, week_ago, limit=1)
    topic = concerns[0]["label"] if concerns else None

    title, body = _tip_for(topic)
    written_by = "library"

    generated = llm.generate_text(
        "You write short, friendly skin-care posts for a dermatology clinic's patients. Plain language, "
        "80 to 120 words, practical and safe. No diagnosis, no prescription medicine names, no promises "
        "of cure, no emojis or hashtags. First line: a title of at most 8 words. Then a blank line, then "
        "the text. Say when to see a dermatologist.",
        f"Topic: {topic or 'a simple daily routine'}.",
        max_tokens=350,
    )
    if generated and "\n" in generated:
        first, rest = generated.split("\n", 1)
        first, rest = first.strip(" #*"), rest.strip()
        if 3 <= len(first) <= 90 and 150 <= len(rest) <= 1500:
            title, body, written_by = first, rest, "llm"

    publish = app_settings.get_bool(db, "agent_posts_auto_publish")
    post = ClinicPost(
        title=title, body=body + POST_FOOTER, kind="tip", source="agent",
        status="published" if publish else "draft",
        published_at=now_utc() if publish else None,
    )
    db.add(post)
    db.commit()
    db.refresh(post)

    if publish:
        emit_post_published(db, post)

    state = "published" if publish else "saved as a draft"
    return (
        f'Post "{title}" {state}.',
        {"post_id": post.id, "topic": topic, "written_by": written_by, "status": post.status},
    )


def emit_post_published(db: Session, post: ClinicPost) -> None:
    automation.emit(db, "post.published", {
        "post_id": post.id, "title": post.title, "body": post.body, "kind": post.kind,
        "url": f"{settings.frontend_url.rstrip('/')}/dashboard",
    })


# ============================================================
# Running
# ============================================================

AGENTS = {
    "daily_report": (daily_report, "Daily clinic report"),
    "appointment_reminders": (appointment_reminders, "Appointment reminders"),
    "daily_post": (daily_post, "Daily skin-care post"),
}


def run_agent(db: Session, name: str, triggered_by: str, run_key: str | None = None) -> AgentRun | None:
    """
    Run one agent and record the result. With a run_key, the run is skipped
    (returns None) when that period was already handled, by this or by any
    other server process.
    """
    function, _label = AGENTS[name]

    run = AgentRun(agent=name, run_key=run_key, triggered_by=triggered_by, status="running")
    db.add(run)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return None
    db.refresh(run)

    try:
        summary, details = function(db)
        run.status, run.summary, run.details = "ok", summary, json.dumps(details, default=str)
    except Exception:
        db.rollback()
        logger.exception("agent_failed", extra={"event": "agent_failed", "agent": name})
        run = db.get(AgentRun, run.id)
        run.status, run.summary = "failed", "The agent stopped with an error. See the server log."
    run.finished_at = now_utc()
    db.commit()
    db.refresh(run)
    return run


def due_runs(now_local: datetime) -> list[tuple[str, str]]:
    """(agent, run_key) pairs the scheduler should make sure have run."""
    due = [("appointment_reminders", f"appointment_reminders:{now_local:%Y-%m-%dT%H}")]
    if now_local.hour >= settings.agent_daily_hour:
        due.append(("daily_report", f"daily_report:{now_local:%Y-%m-%d}"))
        due.append(("daily_post", f"daily_post:{now_local:%Y-%m-%d}"))
    return due
