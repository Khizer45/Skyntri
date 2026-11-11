"""Clinic platform: account fields, runtime settings, doctors, appointments,
prescriptions, payments, automation (API keys, webhooks, agents, posts).

Revision ID: 0005_clinic_platform
Revises: 0004_admin_payments
Create Date: 2026-11-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_clinic_platform"
down_revision = "0004_admin_payments"
branch_labels = None
depends_on = None

NEW_TABLES = [
    "clinic_posts", "agent_runs", "webhook_deliveries", "webhook_endpoints", "api_keys", "payments",
    "consultation_messages", "prescription_items", "prescriptions", "appointments",
    "doctor_availability", "doctor_profiles", "audit_events", "app_settings",
]


def _inspector():
    return sa.inspect(op.get_bind())


def _exists(name: str) -> bool:
    return _inspector().has_table(name)


def _columns(table: str) -> set[str]:
    return {c["name"] for c in _inspector().get_columns(table)}


def _id():
    return sa.Column("id", sa.String(), primary_key=True)


def _ts(name: str = "created_at", nullable: bool = False):
    return sa.Column(name, sa.DateTime(timezone=True), nullable=nullable)


def upgrade() -> None:
    # ---- users -----------------------------------------------------------
    have = _columns("users")
    with op.batch_alter_table("users") as batch:
        if "phone" not in have:
            batch.add_column(sa.Column("phone", sa.String(), nullable=True))
        if "google_sub" not in have:
            batch.add_column(sa.Column("google_sub", sa.String(), nullable=True))
        if "password_set" not in have:
            batch.add_column(sa.Column("password_set", sa.Boolean(), nullable=False, server_default=sa.true()))
        if "email_verified" not in have:
            batch.add_column(sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "google_sub" not in have:
        op.create_index("ix_users_google_sub", "users", ["google_sub"], unique=True)

    if "image_url" not in _columns("chat_messages"):
        with op.batch_alter_table("chat_messages") as batch:
            batch.add_column(sa.Column("image_url", sa.String(), nullable=True))

    # ---- settings and audit ---------------------------------------------
    if not _exists("app_settings"):
        op.create_table(
            "app_settings",
            sa.Column("key", sa.String(), primary_key=True),
            sa.Column("value", sa.Text(), nullable=False),
            sa.Column("updated_by", sa.String(), nullable=True),
            _ts("updated_at"),
        )

    if not _exists("audit_events"):
        op.create_table(
            "audit_events",
            _id(),
            sa.Column("actor", sa.String(), nullable=False),
            sa.Column("action", sa.String(), nullable=False),
            sa.Column("target", sa.String(), nullable=True),
            sa.Column("detail", sa.Text(), nullable=True),
            _ts(),
        )
        op.create_index("ix_audit_events_actor", "audit_events", ["actor"])
        op.create_index("ix_audit_events_action", "audit_events", ["action"])
        op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])

    # ---- clinic ----------------------------------------------------------
    if not _exists("doctor_profiles"):
        op.create_table(
            "doctor_profiles",
            _id(),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False, unique=True),
            sa.Column("specialty", sa.String(), nullable=False),
            sa.Column("qualifications", sa.String(), nullable=False),
            sa.Column("license_number", sa.String(), nullable=False),
            sa.Column("bio", sa.Text(), nullable=True),
            sa.Column("languages", sa.String(), nullable=True),
            sa.Column("years_experience", sa.Integer(), nullable=False),
            sa.Column("consultation_fee", sa.Float(), nullable=False),
            sa.Column("currency", sa.String(), nullable=False),
            sa.Column("slot_minutes", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("reviewed_by", sa.String(), nullable=True),
            _ts("reviewed_at", nullable=True),
            _ts(),
            _ts("updated_at"),
        )
        op.create_index("ix_doctor_profiles_status", "doctor_profiles", ["status"])

    if not _exists("doctor_availability"):
        op.create_table(
            "doctor_availability",
            _id(),
            sa.Column("doctor_id", sa.String(), sa.ForeignKey("doctor_profiles.id"), nullable=False),
            sa.Column("weekday", sa.Integer(), nullable=False),
            sa.Column("start_time", sa.String(), nullable=False),
            sa.Column("end_time", sa.String(), nullable=False),
        )
        op.create_index("ix_doctor_availability_doctor_id", "doctor_availability", ["doctor_id"])
        op.create_index(
            "ux_availability_slot", "doctor_availability", ["doctor_id", "weekday", "start_time"], unique=True
        )

    if not _exists("appointments"):
        op.create_table(
            "appointments",
            _id(),
            sa.Column("patient_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("doctor_id", sa.String(), sa.ForeignKey("doctor_profiles.id"), nullable=False),
            _ts("starts_at"),
            _ts("ends_at"),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("slot_lock", sa.String(), nullable=True, unique=True),
            sa.Column("mode", sa.String(), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("analysis_id", sa.String(), sa.ForeignKey("skin_analyses.id"), nullable=True),
            sa.Column("meeting_url", sa.String(), nullable=True),
            sa.Column("fee", sa.Float(), nullable=False),
            sa.Column("currency", sa.String(), nullable=False),
            sa.Column("payment_status", sa.String(), nullable=False),
            sa.Column("payment_method", sa.String(), nullable=True),
            sa.Column("assessment", sa.Text(), nullable=True),
            sa.Column("private_notes", sa.Text(), nullable=True),
            _ts("follow_up_on", nullable=True),
            sa.Column("cancelled_by", sa.String(), nullable=True),
            sa.Column("cancel_reason", sa.Text(), nullable=True),
            _ts("reminder_sent_at", nullable=True),
            _ts(),
            _ts("updated_at"),
        )
        op.create_index("ix_appointments_patient_id", "appointments", ["patient_id"])
        op.create_index("ix_appointments_doctor_id", "appointments", ["doctor_id"])
        op.create_index("ix_appointments_starts_at", "appointments", ["starts_at"])
        op.create_index("ix_appointments_status", "appointments", ["status"])
        op.create_index("ix_appointments_payment_status", "appointments", ["payment_status"])
        op.create_index("ix_appointments_doctor_start", "appointments", ["doctor_id", "starts_at"])
        op.create_index("ix_appointments_patient_start", "appointments", ["patient_id", "starts_at"])

    if not _exists("prescriptions"):
        op.create_table(
            "prescriptions",
            _id(),
            sa.Column(
                "appointment_id", sa.String(), sa.ForeignKey("appointments.id"), nullable=False, unique=True
            ),
            sa.Column("advice", sa.Text(), nullable=True),
            _ts(),
            _ts("updated_at"),
        )

    if not _exists("prescription_items"):
        op.create_table(
            "prescription_items",
            _id(),
            sa.Column("prescription_id", sa.String(), sa.ForeignKey("prescriptions.id"), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.Column("kind", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("dosage", sa.String(), nullable=True),
            sa.Column("frequency", sa.String(), nullable=True),
            sa.Column("duration", sa.String(), nullable=True),
            sa.Column("instructions", sa.Text(), nullable=True),
        )
        op.create_index("ix_prescription_items_prescription_id", "prescription_items", ["prescription_id"])

    if not _exists("consultation_messages"):
        op.create_table(
            "consultation_messages",
            _id(),
            sa.Column("appointment_id", sa.String(), sa.ForeignKey("appointments.id"), nullable=False),
            sa.Column("sender_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            _ts(),
        )
        op.create_index("ix_consultation_messages_appointment_id", "consultation_messages", ["appointment_id"])

    # ---- payments --------------------------------------------------------
    if not _exists("payments"):
        op.create_table(
            "payments",
            _id(),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("purpose", sa.String(), nullable=False),
            sa.Column("reference_id", sa.String(), nullable=False),
            sa.Column("provider", sa.String(), nullable=False),
            sa.Column("provider_ref", sa.String(), nullable=True, unique=True),
            sa.Column("amount", sa.Float(), nullable=False),
            sa.Column("currency", sa.String(), nullable=False),
            sa.Column("charged_amount", sa.Float(), nullable=False),
            sa.Column("charged_currency", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            _ts(),
            _ts("updated_at"),
        )
        op.create_index("ix_payments_user_id", "payments", ["user_id"])
        op.create_index("ix_payments_status", "payments", ["status"])
        op.create_index("ix_payments_purpose_reference", "payments", ["purpose", "reference_id"])

    # ---- automation ------------------------------------------------------
    if not _exists("api_keys"):
        op.create_table(
            "api_keys",
            _id(),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("prefix", sa.String(), nullable=False),
            sa.Column("key_hash", sa.String(), nullable=False, unique=True),
            sa.Column("scopes", sa.Text(), nullable=False),
            sa.Column("created_by", sa.String(), nullable=True),
            _ts(),
            _ts("last_used_at", nullable=True),
            _ts("revoked_at", nullable=True),
        )
        op.create_index("ix_api_keys_prefix", "api_keys", ["prefix"])

    if not _exists("webhook_endpoints"):
        op.create_table(
            "webhook_endpoints",
            _id(),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("url", sa.String(), nullable=False),
            sa.Column("events", sa.Text(), nullable=False),
            sa.Column("include_contact", sa.Boolean(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_by", sa.String(), nullable=True),
            _ts(),
            _ts("last_delivery_at", nullable=True),
            sa.Column("last_status", sa.String(), nullable=True),
            sa.Column("failure_count", sa.Integer(), nullable=False),
        )

    if not _exists("webhook_deliveries"):
        op.create_table(
            "webhook_deliveries",
            _id(),
            sa.Column("endpoint_id", sa.String(), sa.ForeignKey("webhook_endpoints.id"), nullable=False),
            sa.Column("event", sa.String(), nullable=False),
            sa.Column("payload", sa.Text(), nullable=False),
            sa.Column("ok", sa.Boolean(), nullable=False),
            sa.Column("status_code", sa.Integer(), nullable=True),
            sa.Column("error", sa.String(), nullable=True),
            _ts(),
        )
        op.create_index("ix_webhook_deliveries_endpoint_id", "webhook_deliveries", ["endpoint_id"])
        op.create_index("ix_webhook_deliveries_created_at", "webhook_deliveries", ["created_at"])

    if not _exists("agent_runs"):
        op.create_table(
            "agent_runs",
            _id(),
            sa.Column("agent", sa.String(), nullable=False),
            sa.Column("run_key", sa.String(), nullable=True, unique=True),
            sa.Column("triggered_by", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("details", sa.Text(), nullable=True),
            _ts("started_at"),
            _ts("finished_at", nullable=True),
        )
        op.create_index("ix_agent_runs_agent", "agent_runs", ["agent"])
        op.create_index("ix_agent_runs_started_at", "agent_runs", ["started_at"])

    if not _exists("clinic_posts"):
        op.create_table(
            "clinic_posts",
            _id(),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("kind", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("source", sa.String(), nullable=False),
            _ts(),
            _ts("published_at", nullable=True),
        )
        op.create_index("ix_clinic_posts_status", "clinic_posts", ["status"])
        op.create_index("ix_clinic_posts_published_at", "clinic_posts", ["published_at"])


def downgrade() -> None:
    for table in NEW_TABLES:
        if _exists(table):
            op.drop_table(table)

    with op.batch_alter_table("chat_messages") as batch:
        batch.drop_column("image_url")

    op.drop_index("ix_users_google_sub", table_name="users")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("email_verified")
        batch.drop_column("password_set")
        batch.drop_column("google_sub")
        batch.drop_column("phone")
