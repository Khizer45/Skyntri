"""Request/response models for the clinic: doctors, appointments, prescriptions."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

AppointmentMode = Literal["video", "chat", "in_person"]
ItemKind = Literal["medicine", "treatment", "skincare"]
HHMM = r"^([01]\d|2[0-3]):[0-5]\d$"


# ---------------------------------------------------------------- doctors

class DoctorApplyIn(BaseModel):
    specialty: str = Field(default="Dermatology", min_length=2, max_length=80)
    qualifications: str = Field(min_length=2, max_length=200)
    license_number: str = Field(min_length=3, max_length=60)
    bio: str | None = Field(default=None, max_length=1500)
    languages: str | None = Field(default=None, max_length=120)
    years_experience: int = Field(default=0, ge=0, le=70)
    consultation_fee: float = Field(default=0, ge=0, le=1_000_000)
    slot_minutes: int = Field(default=30, ge=10, le=120)


class DoctorUpdateIn(BaseModel):
    specialty: str | None = Field(default=None, min_length=2, max_length=80)
    qualifications: str | None = Field(default=None, min_length=2, max_length=200)
    bio: str | None = Field(default=None, max_length=1500)
    languages: str | None = Field(default=None, max_length=120)
    years_experience: int | None = Field(default=None, ge=0, le=70)
    consultation_fee: float | None = Field(default=None, ge=0, le=1_000_000)
    slot_minutes: int | None = Field(default=None, ge=10, le=120)


class AvailabilityWindow(BaseModel):
    weekday: int = Field(ge=0, le=6)  # 0 = Monday
    start_time: str = Field(pattern=HHMM)
    end_time: str = Field(pattern=HHMM)

    @field_validator("end_time")
    @classmethod
    def _after_start(cls, value: str, info):
        start = info.data.get("start_time")
        if start and value <= start:
            raise ValueError("end_time must be after start_time")
        return value


class AvailabilityIn(BaseModel):
    windows: list[AvailabilityWindow] = Field(max_length=28)


class DoctorOut(BaseModel):
    id: str
    name: str
    specialty: str
    qualifications: str
    bio: str | None
    languages: str | None
    years_experience: int
    consultation_fee: float
    currency: str
    slot_minutes: int
    avatar_url: str | None = None
    availability: list[AvailabilityWindow] = []


class DoctorSelfOut(DoctorOut):
    status: str
    license_number: str


class AdminDoctorOut(DoctorSelfOut):
    email: str
    phone: str | None
    created_at: datetime
    appointments: int = 0


class AdminDoctorUpdate(BaseModel):
    status: Literal["approved", "rejected", "suspended"]


class SlotOut(BaseModel):
    starts_at: datetime
    ends_at: datetime
    available: bool


# ----------------------------------------------------------- appointments

class AppointmentIn(BaseModel):
    doctor_id: str
    starts_at: datetime
    mode: AppointmentMode = "video"
    reason: str = Field(min_length=5, max_length=1000)
    analysis_id: str | None = None


class CancelIn(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class DoctorAppointmentUpdate(BaseModel):
    status: Literal["confirmed", "completed", "no_show", "cancelled"] | None = None
    meeting_url: str | None = Field(default=None, max_length=500)
    assessment: str | None = Field(default=None, max_length=4000)
    private_notes: str | None = Field(default=None, max_length=4000)
    follow_up_on: datetime | None = None
    cancel_reason: str | None = Field(default=None, max_length=500)

    @field_validator("meeting_url")
    @classmethod
    def _https_only(cls, value: str | None):
        if value and not value.lower().startswith("https://"):
            raise ValueError("The meeting link must start with https://")
        return value


class PrescriptionItemIn(BaseModel):
    kind: ItemKind = "medicine"
    name: str = Field(min_length=1, max_length=160)
    dosage: str | None = Field(default=None, max_length=120)
    frequency: str | None = Field(default=None, max_length=120)
    duration: str | None = Field(default=None, max_length=120)
    instructions: str | None = Field(default=None, max_length=600)


class PrescriptionIn(BaseModel):
    advice: str | None = Field(default=None, max_length=3000)
    items: list[PrescriptionItemIn] = Field(default_factory=list, max_length=30)


class PrescriptionOut(BaseModel):
    advice: str | None
    items: list[PrescriptionItemIn]
    updated_at: datetime


class SharedAnalysisOut(BaseModel):
    id: str
    predicted_condition: str
    severity_level: str
    confidence_score: float
    analysis_track: str | None
    created_at: datetime
    image_url: str | None = None


class AppointmentOut(BaseModel):
    id: str
    status: str
    mode: str
    starts_at: datetime
    ends_at: datetime
    reason: str
    meeting_url: str | None
    fee: float
    currency: str
    payment_status: str
    payment_method: str | None
    assessment: str | None
    follow_up_on: datetime | None
    cancel_reason: str | None
    created_at: datetime

    doctor_id: str
    doctor_name: str
    doctor_specialty: str
    patient_id: str
    patient_name: str

    has_prescription: bool = False
    prescription: PrescriptionOut | None = None
    analysis: SharedAnalysisOut | None = None

    # Doctor (and administrator) view only
    patient_email: str | None = None
    patient_phone: str | None = None
    private_notes: str | None = None


class MessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class MessageOut(BaseModel):
    id: str
    sender: Literal["patient", "doctor"]
    sender_name: str
    body: str
    created_at: datetime
    mine: bool
