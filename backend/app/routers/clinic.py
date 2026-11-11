"""
Online clinic: dermatologists, appointments, consultation messages and
prescriptions.

Who may do what (enforced here, on the server):

* Any signed-in user can list approved doctors, see free slots, book for
  themselves and read / cancel their own appointments.
* A doctor sees only appointments booked with them, and can confirm,
  complete, cancel, add an assessment and write a prescription.
* An administrator approves doctors and sees appointments without the
  doctor's private notes, the messages or the shared photo.
"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import asc, desc, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.db.models import (
    Appointment,
    ConsultationMessage,
    DoctorAvailability,
    DoctorProfile,
    Prescription,
    PrescriptionItem,
    SkinAnalysis,
    User,
)
from app.dependencies import get_current_user, require_admin, require_doctor
from app.schemas_clinic import (
    AdminDoctorOut,
    AdminDoctorUpdate,
    AppointmentIn,
    AppointmentOut,
    AvailabilityIn,
    CancelIn,
    DoctorApplyIn,
    DoctorAppointmentUpdate,
    DoctorOut,
    DoctorSelfOut,
    DoctorUpdateIn,
    MessageIn,
    MessageOut,
    PrescriptionIn,
    PrescriptionOut,
    SlotOut,
)
from app.services import audit, automation, clinic, rate_limit
from app.services.clinic import as_utc, now_utc
from app.services.prescription_pdf import build_prescription_pdf

router = APIRouter(tags=["clinic"])

NOT_FOUND = HTTPException(status.HTTP_404_NOT_FOUND, "Appointment not found.")


# ============================================================
# Doctors (directory)
# ============================================================

def _approved_doctor(db: Session, doctor_id: str) -> DoctorProfile:
    doctor = db.get(DoctorProfile, doctor_id)
    if doctor is None or doctor.status != "approved" or not doctor.user.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Doctor not found.")
    return doctor


@router.get("/doctors", response_model=list[DoctorOut])
def list_doctors(_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doctors = (
        db.query(DoctorProfile)
        .join(User, User.id == DoctorProfile.user_id)
        .filter(DoctorProfile.status == "approved", User.is_active.is_(True))
        .order_by(asc(User.full_name))
        .all()
    )
    return [clinic.doctor_out(d) for d in doctors]


# NOTE: the "/doctors/me" routes are declared before "/doctors/{doctor_id}".

@router.post("/doctors/apply", response_model=DoctorSelfOut, status_code=status.HTTP_201_CREATED)
def apply_as_doctor(
    payload: DoctorApplyIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """A user asks to be listed as a doctor. An administrator must approve."""
    rate_limit.enforce(db, "doctor_apply", current_user.id, 5, timedelta(days=1))

    existing = db.query(DoctorProfile).filter(DoctorProfile.user_id == current_user.id).first()
    if existing is not None and existing.status != "rejected":
        raise HTTPException(status.HTTP_409_CONFLICT, "You already have a doctor profile.")

    doctor = existing or DoctorProfile(user_id=current_user.id)
    for field, value in payload.model_dump().items():
        setattr(doctor, field, value)
    doctor.currency = settings.shop_currency
    doctor.status = "pending"
    doctor.reviewed_by = None
    doctor.reviewed_at = None
    db.add(doctor)
    db.commit()
    db.refresh(doctor)

    automation.emit(db, "doctor.applied", {"doctor_id": doctor.id, "specialty": doctor.specialty})
    return clinic.doctor_self_out(doctor)


def _own_profile(db: Session, user: User) -> DoctorProfile:
    doctor = db.query(DoctorProfile).filter(DoctorProfile.user_id == user.id).first()
    if doctor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "You have no doctor profile.")
    return doctor


@router.get("/doctors/me", response_model=DoctorSelfOut)
def my_doctor_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return clinic.doctor_self_out(_own_profile(db, current_user))


@router.put("/doctors/me", response_model=DoctorSelfOut)
def update_my_doctor_profile(
    payload: DoctorUpdateIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The licence number can only be changed by applying again."""
    doctor = _own_profile(db, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(doctor, field, value)
    db.commit()
    db.refresh(doctor)
    return clinic.doctor_self_out(doctor)


@router.put("/doctors/me/availability", response_model=DoctorSelfOut)
def set_my_availability(
    payload: AvailabilityIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Replace the weekly working hours (clinic time zone)."""
    doctor = _own_profile(db, current_user)

    by_day: dict[int, list] = {}
    for window in payload.windows:
        by_day.setdefault(window.weekday, []).append(window)
    for windows in by_day.values():
        windows.sort(key=lambda w: w.start_time)
        for earlier, later in zip(windows, windows[1:]):
            if later.start_time < earlier.end_time:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Working hours on the same day overlap.")

    doctor.availability.clear()
    db.flush()
    for window in payload.windows:
        doctor.availability.append(
            DoctorAvailability(weekday=window.weekday, start_time=window.start_time, end_time=window.end_time)
        )
    db.commit()
    db.refresh(doctor)
    return clinic.doctor_self_out(doctor)


@router.get("/doctors/{doctor_id}", response_model=DoctorOut)
def get_doctor(doctor_id: str, _user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return clinic.doctor_out(_approved_doctor(db, doctor_id))


@router.get("/doctors/{doctor_id}/slots", response_model=list[SlotOut])
def doctor_slots(
    doctor_id: str,
    day: date = Query(..., description="Date in the clinic time zone, YYYY-MM-DD"),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return clinic.day_slots(db, _approved_doctor(db, doctor_id), day)


# ============================================================
# Appointments (patient)
# ============================================================

@router.post("/appointments", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
def book_appointment(
    payload: AppointmentIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doctor = _approved_doctor(db, payload.doctor_id)
    if doctor.user_id == current_user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot book an appointment with yourself.")

    if payload.starts_at.tzinfo is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The start time must include a time zone.")
    starts_at = as_utc(payload.starts_at).replace(second=0, microsecond=0)

    # The time must be one of the doctor's real, still free slots.
    local_day = starts_at.astimezone(clinic.clinic_tz()).date()
    slot = next((s for s in clinic.day_slots(db, doctor, local_day) if s["starts_at"] == starts_at), None)
    if slot is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The doctor does not work at this time.")
    if not slot["available"]:
        raise HTTPException(status.HTTP_409_CONFLICT, "This time is no longer available. Please choose another.")

    if payload.analysis_id:
        owned = (
            db.query(SkinAnalysis.id)
            .filter(SkinAnalysis.id == payload.analysis_id, SkinAnalysis.user_id == current_user.id)
            .first()
        )
        if not owned:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Skin analysis not found.")

    rate_limit.enforce(
        db, "book_appointment", current_user.id, settings.appointment_bookings_per_day, timedelta(days=1),
        message="You have booked many appointments today. Please try again tomorrow.",
    )

    appointment = Appointment(
        patient_id=current_user.id,
        doctor_id=doctor.id,
        starts_at=starts_at,
        ends_at=slot["ends_at"],
        slot_lock=clinic.slot_lock(doctor.id, starts_at),
        mode=payload.mode,
        reason=payload.reason.strip(),
        analysis_id=payload.analysis_id,
        fee=round(doctor.consultation_fee or 0.0, 2),
        currency=doctor.currency,
        payment_status="unpaid" if (doctor.consultation_fee or 0) > 0 else "not_required",
    )
    db.add(appointment)
    try:
        db.commit()
    except IntegrityError:
        # Another request took the slot between the check and the insert.
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "This time is no longer available. Please choose another."
        ) from None
    db.refresh(appointment)

    data, contact = clinic.event_data(appointment)
    automation.emit(db, "appointment.created", data, contact)
    return clinic.appointment_out(db, appointment, "patient", detail=True)


@router.get("/appointments", response_model=list[AppointmentOut])
def my_appointments(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Appointment)
        .filter(Appointment.patient_id == current_user.id)
        .order_by(desc(Appointment.starts_at))
        .limit(200)
        .all()
    )
    return [clinic.appointment_out(db, a, "patient") for a in rows]


def _viewer(db: Session, appointment: Appointment | None, user: User) -> str:
    """Return "patient" or "doctor" for a participant; 404 for anyone else."""
    if appointment is None:
        raise NOT_FOUND
    if appointment.patient_id == user.id:
        return "patient"
    doctor = appointment.doctor
    if doctor.user_id == user.id and doctor.status == "approved" and user.role == "doctor":
        return "doctor"
    raise NOT_FOUND


@router.get("/appointments/{appointment_id}", response_model=AppointmentOut)
def get_appointment(
    appointment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    appointment = db.get(Appointment, appointment_id)
    return clinic.appointment_out(db, appointment, _viewer(db, appointment, current_user), detail=True)


def _cancel(db: Session, appointment: Appointment, by: str, reason: str | None) -> None:
    appointment.status = "cancelled"
    appointment.slot_lock = None
    appointment.cancelled_by = by
    appointment.cancel_reason = (reason or "").strip() or None
    if appointment.payment_status == "paid":
        # Refunds are made by an administrator in the payment provider.
        appointment.payment_status = "refund_due"


@router.post("/appointments/{appointment_id}/cancel", response_model=AppointmentOut)
def cancel_my_appointment(
    appointment_id: str,
    payload: CancelIn | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    appointment = db.get(Appointment, appointment_id)
    if appointment is None or appointment.patient_id != current_user.id:
        raise NOT_FOUND
    if appointment.status not in clinic.ACTIVE_STATUSES:
        raise HTTPException(status.HTTP_409_CONFLICT, f"A {appointment.status} appointment cannot be cancelled.")
    if as_utc(appointment.starts_at) <= now_utc():
        raise HTTPException(status.HTTP_409_CONFLICT, "This appointment has already started.")

    _cancel(db, appointment, "patient", payload.reason if payload else None)
    db.commit()
    db.refresh(appointment)

    data, contact = clinic.event_data(appointment)
    automation.emit(db, "appointment.updated", data, contact)
    return clinic.appointment_out(db, appointment, "patient", detail=True)


# ============================================================
# Consultation messages (patient <-> doctor)
# ============================================================

def _message_out(message: ConsultationMessage, appointment: Appointment, me: User) -> MessageOut:
    from_patient = message.sender_id == appointment.patient_id
    return MessageOut(
        id=message.id,
        sender="patient" if from_patient else "doctor",
        sender_name=appointment.patient.full_name if from_patient else appointment.doctor.user.full_name,
        body=message.body,
        created_at=message.created_at,
        mine=message.sender_id == me.id,
    )


@router.get("/appointments/{appointment_id}/messages", response_model=list[MessageOut])
def list_messages(
    appointment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    appointment = db.get(Appointment, appointment_id)
    _viewer(db, appointment, current_user)
    return [_message_out(m, appointment, current_user) for m in appointment.messages]


@router.post(
    "/appointments/{appointment_id}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED
)
def send_message(
    appointment_id: str,
    payload: MessageIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    appointment = db.get(Appointment, appointment_id)
    _viewer(db, appointment, current_user)
    if appointment.status in {"cancelled", "no_show"}:
        raise HTTPException(status.HTTP_409_CONFLICT, "This appointment is closed.")

    rate_limit.enforce(db, "consult_msg", current_user.id, settings.consultation_messages_per_hour)

    message = ConsultationMessage(
        appointment_id=appointment.id, sender_id=current_user.id, body=payload.body.strip()
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return _message_out(message, appointment, current_user)


@router.get("/appointments/{appointment_id}/prescription.pdf")
def download_prescription(
    appointment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    appointment = db.get(Appointment, appointment_id)
    _viewer(db, appointment, current_user)
    if appointment.prescription is None and not appointment.assessment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "The doctor has not written a summary yet.")

    return Response(
        content=build_prescription_pdf(appointment),
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="skyntri-prescription.pdf"',
            "Cache-Control": "private, no-store",
        },
    )


# ============================================================
# Doctor portal
# ============================================================

DOCTOR_TRANSITIONS = {
    "requested": {"confirmed", "cancelled"},
    "confirmed": {"completed", "no_show", "cancelled"},
}


def _doctor_appointment(db: Session, doctor: DoctorProfile, appointment_id: str) -> Appointment:
    appointment = db.get(Appointment, appointment_id)
    if appointment is None or appointment.doctor_id != doctor.id:
        raise NOT_FOUND
    return appointment


@router.get("/doctor/appointments", response_model=list[AppointmentOut])
def doctor_appointments(
    scope: str = Query(default="upcoming", pattern="^(upcoming|past|all)$"),
    doctor: DoctorProfile = Depends(require_doctor),
    db: Session = Depends(get_db),
):
    query = db.query(Appointment).filter(Appointment.doctor_id == doctor.id)
    now = now_utc()
    if scope == "upcoming":
        query = query.filter(Appointment.status.in_(clinic.ACTIVE_STATUSES), Appointment.ends_at >= now)
        query = query.order_by(asc(Appointment.starts_at))
    elif scope == "past":
        query = query.filter(
            (Appointment.ends_at < now) | (Appointment.status.notin_(clinic.ACTIVE_STATUSES))
        ).order_by(desc(Appointment.starts_at))
    else:
        query = query.order_by(desc(Appointment.starts_at))
    return [clinic.appointment_out(db, a, "doctor") for a in query.limit(300).all()]


@router.patch("/doctor/appointments/{appointment_id}", response_model=AppointmentOut)
def doctor_update_appointment(
    appointment_id: str,
    payload: DoctorAppointmentUpdate,
    doctor: DoctorProfile = Depends(require_doctor),
    db: Session = Depends(get_db),
):
    appointment = _doctor_appointment(db, doctor, appointment_id)
    fields = payload.model_dump(exclude_unset=True)
    status_changed = False

    new_status = fields.get("status")
    if new_status and new_status != appointment.status:
        if new_status not in DOCTOR_TRANSITIONS.get(appointment.status, set()):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"An appointment cannot go from '{appointment.status}' to '{new_status}'.",
            )
        if new_status in {"completed", "no_show"} and as_utc(appointment.starts_at) > now_utc():
            raise HTTPException(status.HTTP_409_CONFLICT, "This appointment has not started yet.")
        if new_status == "cancelled":
            _cancel(db, appointment, "doctor", fields.get("cancel_reason"))
        else:
            appointment.status = new_status
        status_changed = True
        audit.record(db, doctor.user_id, f"appointment.{new_status}", appointment.id)

    for field in ("meeting_url", "assessment", "private_notes", "follow_up_on"):
        if field in fields:
            value = fields[field]
            setattr(appointment, field, value.strip() or None if isinstance(value, str) else value)

    db.commit()
    db.refresh(appointment)

    if status_changed:
        data, contact = clinic.event_data(appointment)
        automation.emit(db, "appointment.updated", data, contact)
    return clinic.appointment_out(db, appointment, "doctor", detail=True)


@router.put("/doctor/appointments/{appointment_id}/prescription", response_model=PrescriptionOut)
def doctor_write_prescription(
    appointment_id: str,
    payload: PrescriptionIn,
    doctor: DoctorProfile = Depends(require_doctor),
    db: Session = Depends(get_db),
):
    appointment = _doctor_appointment(db, doctor, appointment_id)
    if appointment.status not in {"confirmed", "completed"}:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "A prescription can be written for a confirmed or completed appointment."
        )

    rx = appointment.prescription
    if rx is None:
        rx = Prescription(appointment_id=appointment.id)
        appointment.prescription = rx
    rx.advice = (payload.advice or "").strip() or None
    rx.updated_at = now_utc()
    rx.items.clear()
    db.flush()
    for position, item in enumerate(payload.items):
        rx.items.append(PrescriptionItem(position=position, **item.model_dump()))

    audit.record(db, doctor.user_id, "prescription.saved", appointment.id, f"{len(payload.items)} item(s)")
    db.commit()
    db.refresh(appointment)
    return clinic.prescription_out(appointment)


@router.get("/doctor/patients")
def doctor_patients(doctor: DoctorProfile = Depends(require_doctor), db: Session = Depends(get_db)):
    """People who booked with this doctor, with their visit counts."""
    rows = (
        db.query(
            User.id, User.full_name, User.email, User.phone,
            func.count(Appointment.id), func.max(Appointment.starts_at),
        )
        .join(Appointment, Appointment.patient_id == User.id)
        .filter(Appointment.doctor_id == doctor.id, Appointment.status != "cancelled")
        .group_by(User.id, User.full_name, User.email, User.phone)
        .order_by(desc(func.max(Appointment.starts_at)))
        .limit(500)
        .all()
    )
    return [
        {"id": r[0], "name": r[1], "email": r[2], "phone": r[3], "visits": int(r[4]), "last_visit": r[5]}
        for r in rows
    ]


# ============================================================
# Administration
# ============================================================

def _admin_doctor_out(db: Session, doctor: DoctorProfile) -> AdminDoctorOut:
    count = db.query(func.count(Appointment.id)).filter(Appointment.doctor_id == doctor.id).scalar() or 0
    return clinic.doctor_out(
        doctor, AdminDoctorOut, email=doctor.user.email, phone=doctor.user.phone,
        created_at=doctor.created_at, appointments=int(count),
    )


@router.get("/admin/doctors", response_model=list[AdminDoctorOut])
def admin_list_doctors(_admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    doctors = db.query(DoctorProfile).order_by(desc(DoctorProfile.created_at)).limit(500).all()
    return [_admin_doctor_out(db, d) for d in doctors]


ADMIN_DOCTOR_TRANSITIONS = {
    "pending": {"approved", "rejected"},
    "approved": {"suspended"},
    "suspended": {"approved"},
    "rejected": {"approved"},
}


@router.patch("/admin/doctors/{doctor_id}", response_model=AdminDoctorOut)
def admin_review_doctor(
    doctor_id: str,
    payload: AdminDoctorUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    doctor = db.get(DoctorProfile, doctor_id)
    if doctor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Doctor not found.")
    if payload.status not in ADMIN_DOCTOR_TRANSITIONS.get(doctor.status, set()):
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"A {doctor.status} profile cannot be set to '{payload.status}'."
        )

    doctor.status = payload.status
    doctor.reviewed_by = admin.id
    doctor.reviewed_at = now_utc()

    # The "doctor" role follows the approval. Administrators keep their role.
    user = doctor.user
    if user.role != "admin":
        user.role = "doctor" if payload.status == "approved" else "user"

    audit.record(db, admin.id, f"doctor.{payload.status}", doctor.id, user.email)
    db.commit()
    db.refresh(doctor)
    return _admin_doctor_out(db, doctor)


@router.get("/admin/appointments", response_model=list[AppointmentOut])
def admin_list_appointments(
    status_filter: str | None = Query(default=None, alias="status", max_length=20),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Appointment)
    if status_filter:
        query = query.filter(Appointment.status == status_filter)
    rows = query.order_by(desc(Appointment.starts_at)).limit(300).all()
    return [clinic.appointment_out(db, a, "admin") for a in rows]


@router.patch("/admin/appointments/{appointment_id}/payment", response_model=AppointmentOut)
def admin_update_appointment_payment(
    appointment_id: str,
    payment_status: str = Query(..., pattern="^(paid|refunded)$"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Record a payment taken at the clinic, or a refund made in the provider's dashboard."""
    appointment = db.get(Appointment, appointment_id)
    if appointment is None:
        raise NOT_FOUND
    allowed = {"unpaid": {"paid"}, "paid": {"refunded"}, "refund_due": {"refunded"}}
    if payment_status not in allowed.get(appointment.payment_status, set()):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Payment cannot move from '{appointment.payment_status}' to '{payment_status}'.",
        )
    if payment_status == "paid" and not appointment.payment_method:
        appointment.payment_method = "cash"
    appointment.payment_status = payment_status
    audit.record(db, admin.id, f"appointment.payment_{payment_status}", appointment.id)
    db.commit()
    db.refresh(appointment)
    return clinic.appointment_out(db, appointment, "admin")
