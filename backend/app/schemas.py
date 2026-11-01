from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_serializer

from app.services.uploads import signed_url


# ============================================================
# Common types
# ============================================================

SeverityLevel = Literal[
    "Low",
    "Moderate",
    "High",
]


# ============================================================
# Auth / User
# ============================================================

class RegisterRequest(BaseModel):
    full_name: str = Field(
        min_length=1,
        max_length=120,
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(
        min_length=1,
        max_length=512,
    )

    new_password: str = Field(
        min_length=8,
        max_length=128,
    )


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(
        min_length=1,
        max_length=128,
    )

    new_password: str = Field(
        min_length=8,
        max_length=128,
    )


class UserOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: str
    full_name: str
    email: EmailStr
    skin_type: str
    avatar_url: str | None = None
    role: str = "user"
    notify_analysis: bool
    notify_reports: bool
    created_at: datetime

    @field_serializer("avatar_url")
    def _sign_avatar(self, value: str | None) -> str | None:
        return signed_url(value)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=120,
    )

    skin_type: str | None = Field(
        default=None,
        max_length=50,
    )


class NotificationSettingsRequest(BaseModel):
    notify_analysis: bool
    notify_reports: bool


# ============================================================
# Contact
# ============================================================

class ContactMessageRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=120,
    )

    email: EmailStr

    subject: str = Field(
        min_length=1,
        max_length=200,
    )

    message: str = Field(
        min_length=1,
        max_length=4000,
    )


class ContactSubmitOut(BaseModel):
    id: str
    created_at: datetime
    message: str


class ContactMessageOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: str
    name: str
    email: EmailStr
    subject: str
    message: str
    created_at: datetime


# ============================================================
# Skin analysis
# ============================================================

class SkinAnalysisCreate(BaseModel):
    """
    Compatibility schema for manually saving an already-generated
    analysis result.

    Normal AI flow should use:
        POST /analyses/analyze
    """

    image_url: str | None = None

    predicted_condition: str = Field(
        min_length=1,
        max_length=1000,
    )

    confidence_score: float = Field(
        ge=0,
        le=100,
    )

    severity_level: SeverityLevel = "Low"

    explanation: str | None = Field(
        default=None,
        max_length=4000,
    )


class SkinAnalysisOut(BaseModel):
    """
    Database/history representation of a skin analysis.
    """

    model_config = ConfigDict(
        from_attributes=True,
        protected_namespaces=(),
    )

    id: str
    image_url: str | None
    predicted_condition: str
    confidence_score: float
    severity_level: SeverityLevel
    explanation: str | None
    analysis_track: str | None = "facial_concerns"
    model_version: str | None = None
    created_at: datetime

    @field_serializer("image_url")
    def _sign_image(self, value: str | None) -> str | None:
        return signed_url(value)


class SkinAnalysisRecommendations(BaseModel):
    """
    User-facing recommendation categories.

    These contain readable recommendations only.
    Model probabilities and thresholds are intentionally excluded.
    """

    skincare: list[str] = Field(
        default_factory=list
    )

    ingredients: list[str] = Field(
        default_factory=list
    )

    sun_protection: list[str] = Field(
        default_factory=list
    )

    lifestyle: list[str] = Field(
        default_factory=list
    )

    avoid: list[str] = Field(
        default_factory=list
    )


class SkinAnalysisAnalyzeOut(BaseModel):
    """
    Clean response returned by POST /analyses/analyze.

    Internal model names, thresholds and raw probabilities are not exposed.
    The representative confidence score is retained for the frontend.
    """

    model_config = ConfigDict(protected_namespaces=())

    analysis_id: str
    image_url: str

    conditions: list[str] = Field(
        default_factory=list
    )

    recommendations: SkinAnalysisRecommendations

    confidence_score: float = Field(
        ge=0,
        le=100,
    )

    severity_level: SeverityLevel = "Low"

    disclaimer: str = Field(
        min_length=1,
        max_length=2000,
    )

    analysis_track: str = "facial_concerns"
    analysis_track_label: str = "Facial skin concerns"
    model_version: str | None = None
    gate_version: str | None = None
    status: str = "completed"
    # Model B only: True when a doctor's assessment is recommended.
    referral: bool = False
    summary: str | None = None

    @field_serializer("image_url")
    def _sign_image(self, value: str) -> str:
        return signed_url(value) or value


# ============================================================
# Ingredient scanner
# ============================================================

class IngredientDetail(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=200,
    )

    function: str | None = Field(
        default=None,
        max_length=500,
    )

    status: str = Field(
        min_length=1,
        max_length=50,
    )

    note: str | None = Field(
        default=None,
        max_length=1000,
    )


class IngredientScanCreate(BaseModel):
    image_url: str | None = None

    product_name: str | None = Field(
        default=None,
        max_length=300,
    )

    ingredients: list[IngredientDetail] = Field(
        default_factory=list
    )

    safety_score: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )


class IngredientScanOut(BaseModel):
    """
    Complete frontend-safe ingredient scan response.
    """

    id: str
    image_url: str | None
    product_name: str | None
    total_ingredients: int
    beneficial_count: int
    caution_count: int
    safety_score: float | None
    safety_label: str = "Caution"
    matched_ingredients: list[dict] = Field(
        default_factory=list
    )
    unmatched_ingredients: list[str] = Field(
        default_factory=list
    )
    personalized_warnings: list[str] = Field(
        default_factory=list
    )
    created_at: datetime

    @field_serializer("image_url")
    def _sign_image(self, value: str | None) -> str | None:
        return signed_url(value)


# ============================================================
# Progress checker
# ============================================================

class ProgressCheckOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: str
    before_image_url: str
    after_image_url: str
    status: str
    score: float
    observations: list[str] = Field(
        default_factory=list
    )
    created_at: datetime

    @field_serializer("before_image_url", "after_image_url")
    def _sign_images(self, value: str) -> str:
        return signed_url(value) or value


# ============================================================
# Reports
# ============================================================

class ReportGenerateRequest(BaseModel):
    analysis_id: str | None = None
    progress_id: str | None = None

    title: str = Field(
        default="Skyntri Health Report",
        min_length=1,
        max_length=200,
    )


class ReportOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: str
    title: str
    created_at: datetime


# ============================================================
# History
# ============================================================

class HistoryItemOut(BaseModel):
    id: str
    type: str
    result: str
    confidence: float | None = None
    date: datetime
    status: str


class HistoryResponse(BaseModel):
    analyses: list[HistoryItemOut] = Field(
        default_factory=list
    )

    scans: list[HistoryItemOut] = Field(
        default_factory=list
    )

    progress: list[HistoryItemOut] = Field(
        default_factory=list
    )

    reports: list[HistoryItemOut] = Field(
        default_factory=list
    )


# ============================================================
# AI Assistant chat
# ============================================================

class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=2000,
    )


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: str
    role: str
    content: str
    created_at: datetime