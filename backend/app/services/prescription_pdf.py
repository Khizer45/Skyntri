"""Prescription / visit summary as a PDF (generated in memory, not stored)."""

from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.config import settings
from app.db.models import Appointment
from app.services.clinic import as_utc, clinic_tz

KIND_LABEL = {"medicine": "Medicine", "treatment": "Treatment", "skincare": "Skin care"}


def _p(text: object, style) -> Paragraph:
    return Paragraph(escape(str(text or "")).replace("\n", "<br/>"), style)


def build_prescription_pdf(appointment: Appointment) -> bytes:
    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=10, leading=14)
    small = ParagraphStyle("small", parent=body, fontSize=8.5, leading=11, textColor=colors.HexColor("#6b7280"))
    h1 = ParagraphStyle("h1", parent=styles["Title"], fontSize=18, alignment=0, spaceAfter=2)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=11.5, spaceBefore=10, spaceAfter=4)
    cell = ParagraphStyle("cell", parent=body, fontSize=9, leading=12)

    doctor = appointment.doctor
    patient = appointment.patient
    visit = as_utc(appointment.starts_at).astimezone(clinic_tz())
    rx = appointment.prescription

    story = [
        _p(settings.clinic_name, h1),
        _p("Visit summary and prescription", small),
        Spacer(1, 6 * mm),
    ]

    info = Table(
        [
            [_p("Patient", small), _p(patient.full_name, body), _p("Doctor", small), _p(doctor.user.full_name, body)],
            [
                _p("Visit", small),
                _p(visit.strftime("%d %b %Y, %H:%M") + f" ({settings.clinic_timezone})", body),
                _p("Qualifications", small),
                _p(f"{doctor.qualifications} · Licence {doctor.license_number}", body),
            ],
        ],
        colWidths=[22 * mm, 63 * mm, 27 * mm, 58 * mm],
    )
    info.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.append(info)

    if appointment.assessment:
        story += [_p("Assessment", h2), _p(appointment.assessment, body)]

    if rx and rx.items:
        story.append(_p("Prescription", h2))
        rows = [[_p(t, small) for t in ("Type", "Name", "Dose", "How often", "For how long", "Instructions")]]
        for item in rx.items:
            rows.append(
                [
                    _p(KIND_LABEL.get(item.kind, item.kind), cell),
                    _p(item.name, cell),
                    _p(item.dosage or "-", cell),
                    _p(item.frequency or "-", cell),
                    _p(item.duration or "-", cell),
                    _p(item.instructions or "-", cell),
                ]
            )
        table = Table(rows, colWidths=[20 * mm, 38 * mm, 22 * mm, 24 * mm, 24 * mm, 42 * mm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(table)

    if rx and rx.advice:
        story += [_p("Advice", h2), _p(rx.advice, body)]

    if appointment.follow_up_on:
        follow = as_utc(appointment.follow_up_on).astimezone(clinic_tz())
        story += [_p("Follow-up", h2), _p(follow.strftime("%d %b %Y"), body)]

    story += [
        Spacer(1, 10 * mm),
        _p(
            "Use medicines only as prescribed for you. If your skin gets worse, or you get swelling, "
            "blisters, fever or trouble breathing, stop the product and get medical help at once.",
            small,
        ),
    ]

    buffer = BytesIO()
    SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
        title="Prescription", author=settings.clinic_name,
    ).build(story)
    return buffer.getvalue()
