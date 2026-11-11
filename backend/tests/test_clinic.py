"""Clinic: doctor approval, slots, booking, authorisation, prescriptions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.db.models import Appointment, SkinAnalysis
from tests.conftest import register

APPLY = {"qualifications": "MBBS, FCPS (Dermatology)", "license_number": "PMC-12345",
         "years_experience": 8, "consultation_fee": 2500, "slot_minutes": 30, "bio": "Acne and pigmentation."}
ALL_WEEK = {"windows": [{"weekday": d, "start_time": "09:00", "end_time": "11:00"} for d in range(7)]}


def _admin(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_emails", "boss@test.com")
    return register(client, "boss@test.com")


def _doctor(client, admin, email="doc@test.com", name="Dr Ayesha"):
    headers = register(client, email, name=name)
    profile = client.post("/doctors/apply", json=APPLY, headers=headers)
    assert profile.status_code == 201, profile.text
    assert client.put("/doctors/me/availability", json=ALL_WEEK, headers=headers).status_code == 200
    approved = client.patch(f"/admin/doctors/{profile.json()['id']}", json={"status": "approved"}, headers=admin)
    assert approved.status_code == 200, approved.text
    return headers, profile.json()["id"]


def _free_slot(client, headers, doctor_id, offset=0):
    for ahead in range(1, 5):
        day = (datetime.now(timezone.utc) + timedelta(days=ahead)).date().isoformat()
        slots = [s for s in client.get(f"/doctors/{doctor_id}/slots", params={"day": day}, headers=headers).json()
                 if s["available"]]
        if len(slots) > offset:
            return slots[offset]["starts_at"]
    raise AssertionError("no free slot")


def _book(client, headers, doctor_id, **extra):
    body = {"doctor_id": doctor_id, "starts_at": _free_slot(client, headers, doctor_id),
            "reason": "Acne on both cheeks for 3 months", **extra}
    return client.post("/appointments", json=body, headers=headers)


def test_doctor_must_be_approved_before_listing(api, monkeypatch):
    client, _ = api
    admin = _admin(client, monkeypatch)
    applicant = register(client, "doc@test.com", name="Dr Ayesha")
    patient = register(client, "pat@test.com")

    assert client.get("/doctors").status_code == 401
    profile = client.post("/doctors/apply", json=APPLY, headers=applicant).json()
    assert profile["status"] == "pending"
    assert client.post("/doctors/apply", json=APPLY, headers=applicant).status_code == 409

    # Pending: not listed, not bookable, no doctor portal.
    assert client.get("/doctors", headers=patient).json() == []
    assert client.get(f"/doctors/{profile['id']}", headers=patient).status_code == 404
    assert client.get("/doctor/appointments", headers=applicant).status_code == 403

    # Only an administrator can approve.
    for headers in (patient, applicant):
        assert client.patch(f"/admin/doctors/{profile['id']}", json={"status": "approved"},
                            headers=headers).status_code == 403
    assert client.patch(f"/admin/doctors/{profile['id']}", json={"status": "approved"}, headers=admin).status_code == 200

    listed = client.get("/doctors", headers=patient).json()
    assert [d["name"] for d in listed] == ["Dr Ayesha"]
    assert "license_number" not in listed[0] and "email" not in listed[0]
    assert client.get("/auth/me", headers=applicant).json()["role"] == "doctor"

    # Suspension removes the listing and the portal at once.
    client.patch(f"/admin/doctors/{profile['id']}", json={"status": "suspended"}, headers=admin)
    assert client.get("/doctors", headers=patient).json() == []
    assert client.get("/doctor/appointments", headers=applicant).status_code == 403
    assert client.patch(f"/admin/doctors/{profile['id']}", json={"status": "rejected"}, headers=admin).status_code == 409


def test_availability_validation_and_slots(api, monkeypatch):
    client, _ = api
    admin = _admin(client, monkeypatch)
    doctor, doctor_id = _doctor(client, admin)
    patient = register(client, "pat@test.com")

    overlap = {"windows": [{"weekday": 0, "start_time": "09:00", "end_time": "11:00"},
                           {"weekday": 0, "start_time": "10:30", "end_time": "12:00"}]}
    assert client.put("/doctors/me/availability", json=overlap, headers=doctor).status_code == 400
    backwards = {"windows": [{"weekday": 0, "start_time": "11:00", "end_time": "09:00"}]}
    assert client.put("/doctors/me/availability", json=backwards, headers=doctor).status_code == 422

    day = (datetime.now(timezone.utc) + timedelta(days=2)).date().isoformat()
    slots = client.get(f"/doctors/{doctor_id}/slots", params={"day": day}, headers=patient).json()
    assert len(slots) == 4 and all(s["available"] for s in slots)  # 09:00-11:00 in 30-minute steps
    # 09:00 in Asia/Karachi is 04:00 UTC.
    assert slots[0]["starts_at"].startswith(f"{day}T04:00")


def test_booking_rules_and_double_booking(api, monkeypatch):
    client, SessionLocal = api
    admin = _admin(client, monkeypatch)
    doctor, doctor_id = _doctor(client, admin)
    patient = register(client, "pat@test.com", name="Sara Patient")
    other = register(client, "other@test.com")

    start = _free_slot(client, patient, doctor_id)
    body = {"doctor_id": doctor_id, "starts_at": start, "reason": "Acne on both cheeks"}

    # Outside working hours, in the past, or without a time zone: refused.
    off_hours = start.replace("T04:00", "T15:00").replace("T04:30", "T15:00")
    assert client.post("/appointments", json={**body, "starts_at": off_hours}, headers=patient).status_code == 400
    assert client.post("/appointments", json={**body, "starts_at": "2020-01-01T04:00:00Z"},
                       headers=patient).status_code in (400, 409)
    assert client.post("/appointments", json={**body, "starts_at": start[:19]}, headers=patient).status_code == 400
    # A doctor cannot book with themselves; someone else's analysis cannot be attached.
    assert client.post("/appointments", json=body, headers=doctor).status_code == 400
    with SessionLocal() as db:
        analysis = SkinAnalysis(user_id=_user_id(client, other),
                                predicted_condition="Acne", confidence_score=80.0, severity_level="Low")
        db.add(analysis)
        db.commit()
        foreign_id = analysis.id
    assert client.post("/appointments", json={**body, "analysis_id": foreign_id}, headers=patient).status_code == 404

    booked = client.post("/appointments", json=body, headers=patient)
    assert booked.status_code == 201, booked.text
    appointment = booked.json()
    assert appointment["status"] == "requested" and appointment["fee"] == 2500 and appointment["payment_status"] == "unpaid"
    assert appointment["private_notes"] is None and appointment["patient_email"] is None

    # The same slot cannot be taken twice, and it shows as taken.
    assert client.post("/appointments", json=body, headers=other).status_code == 409
    day = start[:10]
    taken = [s for s in client.get(f"/doctors/{doctor_id}/slots", params={"day": day}, headers=other).json()
             if s["starts_at"] == start]
    assert taken and taken[0]["available"] is False

    # After cancelling, the slot is free again.
    cancelled = client.post(f"/appointments/{appointment['id']}/cancel", json={"reason": "Travelling"}, headers=patient)
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
    assert client.post(f"/appointments/{appointment['id']}/cancel", headers=patient).status_code == 409
    assert client.post("/appointments", json=body, headers=other).status_code == 201


def _user_id(client, headers):
    return client.get("/auth/me", headers=headers).json()["id"]


def test_appointment_privacy_between_users(api, monkeypatch):
    client, _ = api
    admin = _admin(client, monkeypatch)
    doctor, doctor_id = _doctor(client, admin)
    doctor2, doctor2_id = _doctor(client, admin, "doc2@test.com", "Dr Bilal")
    patient = register(client, "pat@test.com")
    stranger = register(client, "stranger@test.com")

    appointment_id = _book(client, patient, doctor_id).json()["id"]

    # A stranger and another doctor get 404 everywhere.
    for headers in (stranger, doctor2):
        assert client.get(f"/appointments/{appointment_id}", headers=headers).status_code == 404
        assert client.get(f"/appointments/{appointment_id}/messages", headers=headers).status_code == 404
        assert client.post(f"/appointments/{appointment_id}/messages", json={"body": "hi"},
                           headers=headers).status_code == 404
        assert client.post(f"/appointments/{appointment_id}/cancel", headers=headers).status_code == 404
        assert client.get(f"/appointments/{appointment_id}/prescription.pdf", headers=headers).status_code == 404
    assert client.patch(f"/doctor/appointments/{appointment_id}", json={"status": "confirmed"},
                        headers=doctor2).status_code == 404
    assert client.put(f"/doctor/appointments/{appointment_id}/prescription", json={"items": []},
                      headers=doctor2).status_code == 404
    assert client.get("/doctor/appointments", headers=doctor2).json() == []
    assert client.get("/doctor/appointments", headers=patient).status_code == 403
    assert client.get("/admin/appointments", headers=patient).status_code == 403
    assert client.get("/appointments", headers=stranger).json() == []

    # Doctor's private notes: visible to the doctor, never to the patient or the admin.
    client.patch(f"/doctor/appointments/{appointment_id}", json={"status": "confirmed", "private_notes": "Rule out PCOS",
                 "meeting_url": "https://meet.example/abc"}, headers=doctor)
    assert client.get(f"/appointments/{appointment_id}", headers=doctor).json()["private_notes"] == "Rule out PCOS"
    as_patient = client.get(f"/appointments/{appointment_id}", headers=patient).json()
    assert as_patient["private_notes"] is None and as_patient["meeting_url"] == "https://meet.example/abc"
    as_admin = client.get("/admin/appointments", headers=admin).json()[0]
    assert as_admin["private_notes"] is None and as_admin["patient_email"] == "pat@test.com"

    # Messages stay between the two participants.
    assert client.post(f"/appointments/{appointment_id}/messages", json={"body": "Should I stop my cream?"},
                       headers=patient).status_code == 201
    assert client.post(f"/appointments/{appointment_id}/messages", json={"body": "Yes, until we talk."},
                       headers=doctor).status_code == 201
    thread = client.get(f"/appointments/{appointment_id}/messages", headers=patient).json()
    assert [(m["sender"], m["mine"]) for m in thread] == [("patient", True), ("doctor", False)]


def test_doctor_workflow_prescription_and_pdf(api, monkeypatch):
    client, SessionLocal = api
    admin = _admin(client, monkeypatch)
    doctor, doctor_id = _doctor(client, admin)
    patient = register(client, "pat@test.com", name="Sara Patient")
    appointment_id = _book(client, patient, doctor_id).json()["id"]
    url = f"/doctor/appointments/{appointment_id}"

    rx = {"advice": "Use sunscreen every morning.", "items": [
        {"kind": "medicine", "name": "Adapalene 0.1% gel", "dosage": "Pea-sized", "frequency": "Once at night",
         "duration": "8 weeks", "instructions": "Avoid the eye area."},
        {"kind": "skincare", "name": "Gentle cleanser", "frequency": "Twice daily"}]}

    # Not before confirmation; cannot complete a future visit; no skipping states.
    assert client.put(f"{url}/prescription", json=rx, headers=doctor).status_code == 409
    assert client.patch(url, json={"status": "completed"}, headers=doctor).status_code == 409
    assert client.patch(url, json={"meeting_url": "http://insecure.example"}, headers=doctor).status_code == 422
    assert client.patch(url, json={"status": "confirmed"}, headers=doctor).json()["status"] == "confirmed"
    assert client.patch(url, json={"status": "completed"}, headers=doctor).status_code == 409  # still in the future

    assert client.put(f"{url}/prescription", json=rx, headers=doctor).status_code == 200
    assert client.put(f"{url}/prescription", json=rx, headers=patient).status_code == 403

    with SessionLocal() as db:  # move the visit into the past
        row = db.get(Appointment, appointment_id)
        row.starts_at = datetime.now(timezone.utc) - timedelta(hours=2)
        row.ends_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()
    done = client.patch(url, json={"status": "completed", "assessment": "Mild comedonal acne."}, headers=doctor)
    assert done.status_code == 200 and done.json()["status"] == "completed"
    assert client.patch(url, json={"status": "cancelled"}, headers=doctor).status_code == 409

    seen = client.get(f"/appointments/{appointment_id}", headers=patient).json()
    assert seen["assessment"] == "Mild comedonal acne."
    assert [i["name"] for i in seen["prescription"]["items"]] == ["Adapalene 0.1% gel", "Gentle cleanser"]

    pdf = client.get(f"/appointments/{appointment_id}/prescription.pdf", headers=patient)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF") and len(pdf.content) > 1500
    assert pdf.headers["cache-control"] == "private, no-store"

    patients = client.get("/doctor/patients", headers=doctor).json()
    assert [(p["name"], p["visits"]) for p in patients] == [("Sara Patient", 1)]
    assert client.get("/admin/stats", headers=admin).json()["clinic"]["doctors"] == 1

    # A patient account can still be deleted; a doctor with patients cannot.
    assert client.delete("/auth/account", headers=doctor).status_code == 409
    assert client.delete("/auth/account", headers=patient).status_code == 204
    assert client.get("/doctor/patients", headers=doctor).json() == []


def test_paid_appointment_cancel_marks_refund_due(api, monkeypatch):
    client, _ = api
    admin = _admin(client, monkeypatch)
    _, doctor_id = _doctor(client, admin)
    patient = register(client, "pat@test.com")
    appointment_id = _book(client, patient, doctor_id).json()["id"]

    pay = f"/admin/appointments/{appointment_id}/payment"
    assert client.patch(pay, params={"payment_status": "refunded"}, headers=admin).status_code == 409
    assert client.patch(pay, params={"payment_status": "paid"}, headers=patient).status_code == 403
    paid = client.patch(pay, params={"payment_status": "paid"}, headers=admin).json()
    assert paid["payment_status"] == "paid" and paid["payment_method"] == "cash"

    cancelled = client.post(f"/appointments/{appointment_id}/cancel", headers=patient).json()
    assert cancelled["payment_status"] == "refund_due"
    assert client.patch(pay, params={"payment_status": "refunded"}, headers=admin).json()["payment_status"] == "refunded"
