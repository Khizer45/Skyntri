from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


# ============================================================
# Common helpers
# ============================================================

def gen_uuid() -> str:
    """
    Generate a UUID string for database primary keys.
    """
    return str(uuid.uuid4())


def utcnow() -> datetime:
    """
    Return the current UTC datetime.

    All application timestamps are stored in UTC.
    """
    return datetime.now(timezone.utc)


# ============================================================
# User
# ============================================================

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=gen_uuid,
    )

    full_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String,
        unique=True,
        index=True,
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    skin_type: Mapped[str] = mapped_column(
        String,
        default="Not set",
        nullable=False,
    )

    avatar_url: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Server-side role (SEC-AUTH-003): "user" (patient), "doctor" or "admin".
    # Never taken from client input. "admin" is granted through ADMIN_EMAILS
    # or the CLI, "doctor" when an administrator approves a doctor profile.
    role: Mapped[str] = mapped_column(
        String,
        default="user",
        server_default="user",
        nullable=False,
    )

    phone: Mapped[str | None] = mapped_column(String, nullable=True)

    # Google account id ("sub") when the account is linked to Google sign-in.
    google_sub: Mapped[str | None] = mapped_column(String, nullable=True, unique=True, index=True)

    # False for accounts created with Google that have not chosen a password
    # yet (their password_hash is a random, unusable value).
    password_set: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1", nullable=False
    )

    # True once the address is proven (Google sign-in). E-mail/password
    # sign-up does not verify the address.
    email_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", nullable=False
    )

    # Notification preferences
    notify_analysis: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    notify_reports: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    # --------------------------------------------------------
    # Relationships
    # --------------------------------------------------------

    analyses: Mapped[list["SkinAnalysis"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    scans: Mapped[list["IngredientScan"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    progress_checks: Mapped[list["ProgressCheck"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    reports: Mapped[list["Report"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    chat_messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # Shop data is removed with the account (SEC-DATA-005).
    cart_items: Mapped[list["CartItem"]] = relationship(
        cascade="all, delete-orphan",
    )

    orders: Mapped[list["Order"]] = relationship(
        cascade="all, delete-orphan",
    )

    # Clinic data of a patient is removed with the account as well.
    appointments: Mapped[list["Appointment"]] = relationship(
        cascade="all, delete-orphan",
        foreign_keys="Appointment.patient_id",
        overlaps="patient",
    )

    payments: Mapped[list["Payment"]] = relationship(
        cascade="all, delete-orphan",
    )

    @property
    def google_linked(self) -> bool:
        return bool(self.google_sub)


# ============================================================
# Password reset token
# ============================================================

class PasswordResetToken(Base):
    """
    Password-reset token storage.

    SECURITY (SEC-AUTH-007): the `token` column stores only the SHA-256
    digest of the random token that is e-mailed to the user. The raw token
    is never stored, logged in production, or returned by the API. Tokens
    are single-use and expire after PASSWORD_RESET_TOKEN_MINUTES.
    """

    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=gen_uuid,
    )

    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    token: Mapped[str] = mapped_column(
        String,
        unique=True,
        index=True,
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    used: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )


# ============================================================
# Contact messages
# ============================================================

class ContactMessage(Base):
    """
    Stores messages submitted through the Contact/Help section.
    """

    __tablename__ = "contact_messages"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=gen_uuid,
    )

    name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    subject: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )


# ============================================================
# Skin analysis
# ============================================================

class SkinAnalysis(Base):
    """
    Stores the result of Skyntri's AI skin-analysis pipeline.

    Current flow:

        uploaded image
            ↓
        preprocessing
            ↓
        Dataset 1 model
            ↓
        Dataset 3 model
            ↓
        combined visible conditions
            ↓
        AI-estimated visible-pattern severity
            ↓
        recommendations
            ↓
        database

    The database stores the clean result needed for:
        - analysis history
        - dashboard
        - progress comparison
        - reports
        - frontend display

    Raw model probabilities and model-specific thresholds are NOT
    stored in this table.
    """

    __tablename__ = "skin_analyses"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=gen_uuid,
    )

    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    image_url: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    predicted_condition: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    # Percentage value from 0 to 100.
    #
    # Current API keeps Dataset 1 representative confidence here
    # for compatibility with the existing schema/database design.
    # It is NOT the medical severity score.
    confidence_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    # AI-estimated visible-pattern severity:
    # Low / Moderate / High
    #
    # This is intentionally not described as medical severity.
    severity_level: Mapped[str] = mapped_column(
        String,
        default="Low",
        nullable=False,
    )

    explanation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Which analysis track produced the result (FR-06):
    #   facial_concerns    -> Model A
    #   disease_screening  -> Model B (not released yet)
    # Historical rows without a value were produced by Model A.
    analysis_track: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        default="facial_concerns",
    )

    model_version: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    gate_version: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        back_populates="analyses"
    )

    __table_args__ = (
        Index(
            "ix_skin_analyses_user_created",
            "user_id",
            "created_at",
        ),
    )


# ============================================================
# Ingredient scan
# ============================================================

class IngredientScan(Base):
    """
    Stores the result of an ingredient-label scan.

    Current intended pipeline:

        ingredient image
            ↓
        OCR
            ↓
        ingredient extraction
            ↓
        normalization/matching
            ↓
        ingredient safety database
            ↓
        skin-condition-aware result
            ↓
        database
    """

    __tablename__ = "ingredient_scans"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=gen_uuid,
    )

    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    image_url: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    product_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    total_ingredients: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )

    beneficial_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )

    caution_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )

    safety_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # JSON-encoded detailed ingredient analysis.
    details_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        back_populates="scans"
    )

    __table_args__ = (
        Index(
            "ix_ingredient_scans_user_created",
            "user_id",
            "created_at",
        ),
    )

# ============================================================
# Ingredient database
# ============================================================

class Ingredient(Base):
    """
    Curated skincare ingredient database used by:

        - Ingredient Scanner
        - OCR ingredient matching
        - skin-type personalization
        - ingredient search API
        - ingredient safety analysis

    JSON fields are stored as TEXT because the current SQLite
    database design uses JSON-encoded lists.
    """

    __tablename__ = "ingredients"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=gen_uuid,
    )

    # --------------------------------------------------------
    # Basic identity
    # --------------------------------------------------------

    name: Mapped[str] = mapped_column(
        String,
        unique=True,
        index=True,
        nullable=False,
    )

    inci_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )

    # JSON-encoded list:
    # ["Glycerol", "other label spelling"]
    aliases_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # --------------------------------------------------------
    # Ingredient classification
    # --------------------------------------------------------

    category: Mapped[str] = mapped_column(
        String,
        index=True,
        nullable=False,
    )

    function: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # JSON-encoded list:
    # ["Hydration", "Barrier support"]
    uses_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # --------------------------------------------------------
    # Safety information
    # --------------------------------------------------------

    safety_status: Mapped[str] = mapped_column(
        String,
        index=True,
        nullable=False,
    )

    safety_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    # JSON-encoded list:
    # ["Normal", "Dry", "Sensitive"]
    suitable_skin_types_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # JSON-encoded list:
    # ["Oily", "Sensitive"]
    avoid_skin_types_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # --------------------------------------------------------
    # Usage / precautions
    # --------------------------------------------------------

    when_to_use: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    precautions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    __table_args__ = (
        Index(
            "ix_ingredients_category_safety",
            "category",
            "safety_status",
        ),
    )
# ============================================================
# Progress checks
# ============================================================

class ProgressCheck(Base):
    """
    Stores before/after skin-progress comparisons.

    The current service performs image-based heuristic analysis
    using visual signals such as:
        - redness
        - texture
        - affected-area estimate
        - percentage change

    This is an AI/CV-style visual comparison metric, but it is NOT
    a clinical measurement or medical diagnosis.
    """

    __tablename__ = "progress_checks"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=gen_uuid,
    )

    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    before_image_url: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    after_image_url: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String,
        default="Pending",
        nullable=False,
    )

    # Improvement score represented as a percentage-like value.
    score: Mapped[float] = mapped_column(
        Float,
        default=0,
        nullable=False,
    )

    # JSON-encoded observations/metrics.
    observations_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        back_populates="progress_checks"
    )

    __table_args__ = (
        Index(
            "ix_progress_checks_user_created",
            "user_id",
            "created_at",
        ),
    )


# ============================================================
# Reports
# ============================================================

class Report(Base):
    """
    Stores generated Skyntri PDF report metadata.

    The actual PDF file is stored on disk and file_path points
    to its location.
    """

    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=gen_uuid,
    )

    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String,
        default="Skyntri Health Report",
        nullable=False,
    )

    file_path: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    analysis_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("skin_analyses.id"),
        nullable=True,
        index=True,
    )

    progress_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("progress_checks.id"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        back_populates="reports"
    )


# ============================================================
# Chat messages
# ============================================================

class ChatMessage(Base):
    """
    Stores Skyntri AI Assistant conversation history.

    Current architecture:

        user message
            ↓
        safety / intent layer
            ↓
        local assistant response

    The service layer is prepared for future LLM integration
    (OpenAI primary, optional Gemini fallback) while retaining
    the local safety/rule-based fallback.
    """

    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=gen_uuid,
    )

    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Private upload reference of a generated illustration, if any.
    image_url: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        back_populates="chat_messages"
    )

    __table_args__ = (
        Index(
            "ix_chat_messages_user_created",
            "user_id",
            "created_at",
        ),
    )


# ============================================================
# Rate-limit events
# ============================================================

class RateLimitEvent(Base):
    """
    One row per rate-limited action (login failure, reset request, upload,
    chat message ...). Stored in the shared database so limits are enforced
    consistently across workers and instances (SK-07 / SEC-APP-005).

    Keys are hashed so e-mail addresses and IPs are not stored in clear.
    Old rows are pruned opportunistically.
    """

    __tablename__ = "rate_limit_events"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=gen_uuid,
    )

    bucket: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    key_hash: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    __table_args__ = (
        Index(
            "ix_rate_limit_bucket_key_created",
            "bucket",
            "key_hash",
            "created_at",
        ),
    )


# ============================================================
# Shop: products, cart, orders
# ============================================================

class Product(Base):
    """
    Skincare product managed by administrators.

    Prices are entered by an admin together with their source and the date
    they were checked (SEC-PROD-001/002). Nothing is invented by the app.
    """

    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    brand: Mapped[str] = mapped_column(String, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    size: Mapped[str | None] = mapped_column(String, nullable=True)

    # JSON-encoded list of ingredient names as written on the label (INCI order)
    ingredients_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    # JSON-encoded list of canonical comparison keys (computed on save)
    ingredient_keys_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    skin_types_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    concerns_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="PKR")
    price_source: Mapped[str | None] = mapped_column(String, nullable=True)
    price_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    stock: Mapped[int] = mapped_column(default=0, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_sponsored: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(String, ForeignKey("products.id"), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    product: Mapped["Product"] = relationship()

    __table_args__ = (
        Index("ux_cart_user_product", "user_id", "product_id", unique=True),
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)

    # pending -> confirmed -> shipped -> delivered ; pending/confirmed -> cancelled
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False, index=True)
    payment_method: Mapped[str] = mapped_column(String, default="cash_on_delivery", nullable=False)
    # unpaid -> paid (cash collected) -> refunded
    payment_status: Mapped[str] = mapped_column(
        String, default="unpaid", server_default="unpaid", nullable=False, index=True
    )

    subtotal: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="PKR")

    shipping_name: Mapped[str] = mapped_column(String, nullable=False)
    shipping_phone: Mapped[str] = mapped_column(String, nullable=False)
    shipping_address: Mapped[str] = mapped_column(Text, nullable=False)
    shipping_city: Mapped[str] = mapped_column(String, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_orders_user_created", "user_id", "created_at"),
    )


class OrderItem(Base):
    """Snapshot of the product at purchase time (survives product edits/deletes)."""

    __tablename__ = "order_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    order_id: Mapped[str] = mapped_column(String, ForeignKey("orders.id"), nullable=False, index=True)
    product_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    product_name: Mapped[str] = mapped_column(String, nullable=False)
    brand: Mapped[str] = mapped_column(String, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    line_total: Mapped[float] = mapped_column(Float, nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")


# ============================================================
# Runtime settings and audit trail
# ============================================================

class AppSetting(Base):
    """Settings an administrator can change while the app is running."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_by: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class AuditEvent(Base):
    """Who did what: administrator, doctor and automation actions."""

    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    # User id, or "api_key:<id>" / "system" for automation.
    actor: Mapped[str] = mapped_column(String, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String, nullable=False, index=True)
    target: Mapped[str | None] = mapped_column(String, nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )


# ============================================================
# Clinic: doctors, appointments, prescriptions
# ============================================================

class DoctorProfile(Base):
    """
    A dermatologist's public profile. A user applies, an administrator
    checks the licence and approves; only approved doctors are listed and
    can be booked.
    """

    __tablename__ = "doctor_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, unique=True)

    specialty: Mapped[str] = mapped_column(String, nullable=False, default="Dermatology")
    qualifications: Mapped[str] = mapped_column(String, nullable=False)
    license_number: Mapped[str] = mapped_column(String, nullable=False)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    languages: Mapped[str | None] = mapped_column(String, nullable=True)
    years_experience: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    consultation_fee: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    currency: Mapped[str] = mapped_column(String, default="PKR", nullable=False)
    slot_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

    # pending -> approved | rejected ; approved <-> suspended
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False, index=True)
    reviewed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    user: Mapped["User"] = relationship()
    availability: Mapped[list["DoctorAvailability"]] = relationship(
        back_populates="doctor", cascade="all, delete-orphan"
    )


class DoctorAvailability(Base):
    """Weekly working hours in the clinic time zone (CLINIC_TIMEZONE)."""

    __tablename__ = "doctor_availability"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    doctor_id: Mapped[str] = mapped_column(String, ForeignKey("doctor_profiles.id"), nullable=False, index=True)
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)  # 0 = Monday
    start_time: Mapped[str] = mapped_column(String, nullable=False)  # "HH:MM"
    end_time: Mapped[str] = mapped_column(String, nullable=False)

    doctor: Mapped["DoctorProfile"] = relationship(back_populates="availability")

    __table_args__ = (
        Index("ux_availability_slot", "doctor_id", "weekday", "start_time", unique=True),
    )


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    patient_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    doctor_id: Mapped[str] = mapped_column(String, ForeignKey("doctor_profiles.id"), nullable=False, index=True)

    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # requested -> confirmed -> completed | no_show ; requested/confirmed -> cancelled
    status: Mapped[str] = mapped_column(String, default="requested", nullable=False, index=True)
    # "<doctor id>|<start>" while the slot is taken, NULL once cancelled. The
    # unique index makes double booking impossible, also across workers.
    slot_lock: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)

    mode: Mapped[str] = mapped_column(String, default="video", nullable=False)  # video | chat | in_person
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    # A skin analysis the patient chose to show the doctor.
    analysis_id: Mapped[str | None] = mapped_column(String, ForeignKey("skin_analyses.id"), nullable=True)
    meeting_url: Mapped[str | None] = mapped_column(String, nullable=True)

    fee: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    currency: Mapped[str] = mapped_column(String, default="PKR", nullable=False)
    payment_status: Mapped[str] = mapped_column(String, default="unpaid", nullable=False, index=True)
    payment_method: Mapped[str | None] = mapped_column(String, nullable=True)

    # Written by the doctor; the patient sees the assessment and follow-up.
    assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    private_notes: Mapped[str | None] = mapped_column(Text, nullable=True)  # doctor only
    follow_up_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    cancelled_by: Mapped[str | None] = mapped_column(String, nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    patient: Mapped["User"] = relationship(foreign_keys=[patient_id])
    doctor: Mapped["DoctorProfile"] = relationship()
    prescription: Mapped["Prescription | None"] = relationship(
        back_populates="appointment", cascade="all, delete-orphan", uselist=False
    )
    messages: Mapped[list["ConsultationMessage"]] = relationship(
        cascade="all, delete-orphan", order_by="ConsultationMessage.created_at"
    )

    __table_args__ = (
        Index("ix_appointments_doctor_start", "doctor_id", "starts_at"),
        Index("ix_appointments_patient_start", "patient_id", "starts_at"),
    )


class Prescription(Base):
    """Medicines, treatments and skin-care advice written by the doctor."""

    __tablename__ = "prescriptions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    appointment_id: Mapped[str] = mapped_column(
        String, ForeignKey("appointments.id"), nullable=False, unique=True
    )
    advice: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    appointment: Mapped["Appointment"] = relationship(back_populates="prescription")
    items: Mapped[list["PrescriptionItem"]] = relationship(
        back_populates="prescription", cascade="all, delete-orphan", order_by="PrescriptionItem.position"
    )


class PrescriptionItem(Base):
    __tablename__ = "prescription_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    prescription_id: Mapped[str] = mapped_column(
        String, ForeignKey("prescriptions.id"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    kind: Mapped[str] = mapped_column(String, default="medicine", nullable=False)  # medicine | treatment | skincare
    name: Mapped[str] = mapped_column(String, nullable=False)
    dosage: Mapped[str | None] = mapped_column(String, nullable=True)
    frequency: Mapped[str | None] = mapped_column(String, nullable=True)
    duration: Mapped[str | None] = mapped_column(String, nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    prescription: Mapped["Prescription"] = relationship(back_populates="items")


class ConsultationMessage(Base):
    """Messages between the patient and the doctor of one appointment."""

    __tablename__ = "consultation_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    appointment_id: Mapped[str] = mapped_column(
        String, ForeignKey("appointments.id"), nullable=False, index=True
    )
    sender_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# ============================================================
# Payments
# ============================================================

class Payment(Base):
    """
    One attempt to pay an order or an appointment with an online provider.
    Card numbers never reach this application: the customer pays on the
    provider's page and only the provider's reference is stored.
    """

    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    purpose: Mapped[str] = mapped_column(String, nullable=False)  # order | appointment
    reference_id: Mapped[str] = mapped_column(String, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)  # stripe | paypal
    provider_ref: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)

    # Amount due in the shop currency, and what the provider was asked to charge.
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False)
    charged_amount: Mapped[float] = mapped_column(Float, nullable=False)
    charged_currency: Mapped[str] = mapped_column(String, nullable=False)

    # created -> succeeded | failed | cancelled ; succeeded -> refunded
    status: Mapped[str] = mapped_column(String, default="created", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    __table_args__ = (
        Index("ix_payments_purpose_reference", "purpose", "reference_id"),
    )


# ============================================================
# Automation: API keys, webhooks, agents, clinic posts
# ============================================================

class ApiKey(Base):
    """Key for automation tools (n8n, Zapier, custom agents). Only a hash is stored."""

    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    prefix: Mapped[str] = mapped_column(String, nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    scopes: Mapped[str] = mapped_column(Text, nullable=False, default="")  # comma-separated
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WebhookEndpoint(Base):
    """A URL that receives signed event notifications (n8n / Zapier webhook)."""

    __tablename__ = "webhook_endpoints"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    events: Mapped[str] = mapped_column(Text, nullable=False, default="*")  # comma-separated or "*"
    # Include the patient's name, e-mail and phone in appointment events
    # (needed for reminder workflows). Off: only ids are sent.
    include_contact: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_delivery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[str | None] = mapped_column(String, nullable=True)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    endpoint_id: Mapped[str] = mapped_column(
        String, ForeignKey("webhook_endpoints.id"), nullable=False, index=True
    )
    event: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    ok: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )


class AgentRun(Base):
    """One run of a built-in agent (daily report, reminders, daily post)."""

    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    agent: Mapped[str] = mapped_column(String, nullable=False, index=True)
    # "<agent>:<period>" for scheduled runs, so a period is never run twice.
    run_key: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    triggered_by: Mapped[str] = mapped_column(String, nullable=False, default="schedule")
    status: Mapped[str] = mapped_column(String, nullable=False, default="running")  # running | ok | failed
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ClinicPost(Base):
    """Clinic updates and skin-care tips shown to signed-in users."""

    __tablename__ = "clinic_posts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False, default="tip")  # tip | announcement
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft", index=True)  # draft | published
    source: Mapped[str] = mapped_column(String, nullable=False, default="admin")  # admin | agent | api
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
