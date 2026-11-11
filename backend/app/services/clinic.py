"""Clinic rules: working hours, bookable slots, serialisation."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Appointment, DoctorProfile, SkinAnalysis, User
from app.schemas_clinic import (
    AppointmentOut,
    AvailabilityWindow,
    DoctorOut,
    DoctorSelfOut,
    PrescriptionItemIn,
    PrescriptionOut,
    SharedAnalysisOut,
)
from app.services.uploads import signed_url

ACTIVE_STATUSES = ("requested", "confirmed")


def clinic_tz() -> ZoneInfo:
    try:
        return ZoneInfo(settings.clinic_timezone)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def as_utc(value: datetime) -> datetime:
    """SQLite returns naive datetimes; all stored times are UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _hhmm(value: str) -> time:
    hours, minutes = value.split(":")
    return time(int(hours), int(minutes))


def slot_lock(doctor_id: str, starts_at: datetime) -> str:
    return f"{doctor_id}|{as_utc(starts_at).strftime('%Y-%m-%dT%H:%M')}"


def day_slots(db: Session, doctor: DoctorProfile, day: date) -> list[dict]:
    """All slots of `day` (clinic time zone) with whether each can be booked."""
    tz = clinic_tz()
    now = now_utc()
    earliest = now + timedelta(minutes=settings.appointment_min_notice_minutes)
    latest = now + timedelta(days=settings.appointment_max_days_ahead)
    step = timedelta(minutes=doctor.slot_minutes or 30)

    day_start = datetime.combine(day, time.min, tzinfo=tz).astimezone(timezone.utc)
    taken = {
        as_utc(row[0]).replace(second=0, microsecond=0)
        for row in db.query(Appointment.starts_at)
        .filter(
            Appointment.doctor_id == doctor.id,
            Appointment.status.in_(ACTIVE_STATUSES),
            Appointment.starts_at >= day_start,
            Appointment.starts_at < day_start + timedelta(days=1, hours=2),
        )
        .all()
    }

    slots: list[dict] = []
    windows = sorted(
        (w for w in doctor.availability if w.weekday == day.weekday()), key=lambda w: w.start_time
    )
    for window in windows:
        cursor = datetime.combine(day, _hhmm(window.start_time), tzinfo=tz)
        end = datetime.combine(day, _hhmm(window.end_time), tzinfo=tz)
        while cursor + step <= end:
            start_utc = cursor.astimezone(timezone.utc)
            slots.append(
                {
                    "starts_at": start_utc,
                    "ends_at": start_utc + step,
                    "available": earliest <= start_utc <= latest and start_utc not in taken,
                }
            )
            cursor += step
    return slots


# ---------------------------------------------------------------- output

def doctor_out(doctor: DoctorProfile, model=DoctorOut, **extra):
    user: User = doctor.user
    data = dict(
        id=doctor.id,
        name=user.full_name,
        specialty=doctor.specialty,
        qualifications=doctor.qualifications,
        bio=doctor.bio,
        languages=doctor.languages,
        years_experience=doctor.years_experience,
        consultation_fee=round(doctor.consultation_fee or 0.0, 2),
        currency=doctor.currency,
        slot_minutes=doctor.slot_minutes,
        avatar_url=signed_url(user.avatar_url),
        availability=[
            AvailabilityWindow(weekday=w.weekday, start_time=w.start_time, end_time=w.end_time)
            for w in sorted(doctor.availability, key=lambda w: (w.weekday, w.start_time))
        ],
    )
    if model is not DoctorOut:
        data.update(status=doctor.status, license_number=doctor.license_number)
    data.update(extra)
    return model(**data)


def doctor_self_out(doctor: DoctorProfile) -> DoctorSelfOut:
    return doctor_out(doctor, DoctorSelfOut)


def prescription_out(appointment: Appointment) -> PrescriptionOut | None:
    rx = appointment.prescription
    if rx is None:
        return None
    return PrescriptionOut(
        advice=rx.advice,
        updated_at=rx.updated_at,
        items=[
            PrescriptionItemIn(
                kind=i.kind, name=i.name, dosage=i.dosage, frequency=i.frequency,
                duration=i.duration, instructions=i.instructions,
            )
            for i in rx.items
        ],
    )


def appointment_out(db: Session, appointment: Appointment, viewer: str, detail: bool = False) -> AppointmentOut:
    """
    viewer: "patient", "doctor" or "admin".
    The doctor's private notes are never shown to the patient. The shared
    analysis photo is shown to the patient and to the treating doctor only.
    """
    doctor = appointment.doctor
    patient = appointment.patient
    staff = viewer in {"doctor", "admin"}

    analysis = None
    if detail and appointment.analysis_id:
        row = db.get(SkinAnalysis, appointment.analysis_id)
        if row is not None:
            analysis = SharedAnalysisOut(
                id=row.id,
                predicted_condition=row.predicted_condition,
                severity_level=row.severity_level,
                confidence_score=row.confidence_score,
                analysis_track=row.analysis_track,
                created_at=row.created_at,
                image_url=signed_url(row.image_url) if viewer in {"patient", "doctor"} else None,
            )

    return AppointmentOut(
        id=appointment.id,
        status=appointment.status,
        mode=appointment.mode,
        starts_at=as_utc(appointment.starts_at),
        ends_at=as_utc(appointment.ends_at),
        reason=appointment.reason,
        meeting_url=appointment.meeting_url if appointment.status == "confirmed" or staff else None,
        fee=round(appointment.fee or 0.0, 2),
        currency=appointment.currency,
        payment_status=appointment.payment_status,
        payment_method=appointment.payment_method,
        assessment=appointment.assessment,
        follow_up_on=appointment.follow_up_on,
        cancel_reason=appointment.cancel_reason,
        created_at=appointment.created_at,
        doctor_id=doctor.id,
        doctor_name=doctor.user.full_name,
        doctor_specialty=doctor.specialty,
        patient_id=patient.id,
        patient_name=patient.full_name,
        has_prescription=appointment.prescription is not None,
        prescription=prescription_out(appointment) if detail else None,
        analysis=analysis,
        patient_email=patient.email if staff else None,
        patient_phone=patient.phone if staff else None,
        private_notes=appointment.private_notes if viewer == "doctor" else None,
    )


def event_data(appointment: Appointment) -> tuple[dict, dict]:
    """Webhook payload (no medical details) and the optional contact block."""
    patient = appointment.patient
    data = {
        "appointment_id": appointment.id,
        "status": appointment.status,
        "mode": appointment.mode,
        "starts_at": as_utc(appointment.starts_at).isoformat(),
        "ends_at": as_utc(appointment.ends_at).isoformat(),
        "timezone": settings.clinic_timezone,
        "doctor_id": appointment.doctor_id,
        "doctor_name": appointment.doctor.user.full_name,
        "patient_id": patient.id,
        "payment_status": appointment.payment_status,
    }
    contact = {"name": patient.full_name, "email": patient.email, "phone": patient.phone}
    return data, contact
