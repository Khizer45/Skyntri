"""Baseline schema (matches the pre-migration create_all schema).

Each table is created only if it does not exist yet, so this revision can be
applied both to a fresh database and to an existing database that was
created earlier by SQLAlchemy create_all().

Revision ID: 0001_baseline
Revises:
Create Date: 2026-10-31
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def _exists(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def _ts():
    return sa.Column("created_at", sa.DateTime(timezone=True), nullable=False)


def upgrade() -> None:
    if not _exists("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("full_name", sa.String(), nullable=False),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("password_hash", sa.String(), nullable=False),
            sa.Column("skin_type", sa.String(), nullable=False),
            sa.Column("avatar_url", sa.String(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("notify_analysis", sa.Boolean(), nullable=False),
            sa.Column("notify_reports", sa.Boolean(), nullable=False),
            _ts(),
        )
        op.create_index("ix_users_email", "users", ["email"], unique=True)

    if not _exists("password_reset_tokens"):
        op.create_table(
            "password_reset_tokens",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("token", sa.String(), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used", sa.Boolean(), nullable=False),
            _ts(),
        )
        op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
        op.create_index("ix_password_reset_tokens_token", "password_reset_tokens", ["token"], unique=True)

    if not _exists("contact_messages"):
        op.create_table(
            "contact_messages",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("subject", sa.String(), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            _ts(),
        )

    if not _exists("skin_analyses"):
        op.create_table(
            "skin_analyses",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("image_url", sa.String(), nullable=True),
            sa.Column("predicted_condition", sa.String(), nullable=False),
            sa.Column("confidence_score", sa.Float(), nullable=False),
            sa.Column("severity_level", sa.String(), nullable=False),
            sa.Column("explanation", sa.Text(), nullable=True),
            _ts(),
        )
        op.create_index("ix_skin_analyses_user_id", "skin_analyses", ["user_id"])
        op.create_index("ix_skin_analyses_user_created", "skin_analyses", ["user_id", "created_at"])

    if not _exists("ingredient_scans"):
        op.create_table(
            "ingredient_scans",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("image_url", sa.String(), nullable=True),
            sa.Column("product_name", sa.String(), nullable=True),
            sa.Column("total_ingredients", sa.Integer(), nullable=False),
            sa.Column("beneficial_count", sa.Integer(), nullable=False),
            sa.Column("caution_count", sa.Integer(), nullable=False),
            sa.Column("safety_score", sa.Float(), nullable=True),
            sa.Column("details_json", sa.Text(), nullable=True),
            _ts(),
        )
        op.create_index("ix_ingredient_scans_user_id", "ingredient_scans", ["user_id"])
        op.create_index("ix_ingredient_scans_user_created", "ingredient_scans", ["user_id", "created_at"])

    if not _exists("ingredients"):
        op.create_table(
            "ingredients",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("inci_name", sa.String(), nullable=True),
            sa.Column("aliases_json", sa.Text(), nullable=True),
            sa.Column("category", sa.String(), nullable=False),
            sa.Column("function", sa.Text(), nullable=False),
            sa.Column("uses_json", sa.Text(), nullable=True),
            sa.Column("safety_status", sa.String(), nullable=False),
            sa.Column("safety_score", sa.Float(), nullable=False),
            sa.Column("suitable_skin_types_json", sa.Text(), nullable=True),
            sa.Column("avoid_skin_types_json", sa.Text(), nullable=True),
            sa.Column("when_to_use", sa.Text(), nullable=True),
            sa.Column("precautions", sa.Text(), nullable=True),
            _ts(),
        )
        op.create_index("ix_ingredients_name", "ingredients", ["name"], unique=True)
        op.create_index("ix_ingredients_inci_name", "ingredients", ["inci_name"])
        op.create_index("ix_ingredients_category", "ingredients", ["category"])
        op.create_index("ix_ingredients_safety_status", "ingredients", ["safety_status"])
        op.create_index("ix_ingredients_category_safety", "ingredients", ["category", "safety_status"])

    if not _exists("progress_checks"):
        op.create_table(
            "progress_checks",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("before_image_url", sa.String(), nullable=False),
            sa.Column("after_image_url", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("score", sa.Float(), nullable=False),
            sa.Column("observations_json", sa.Text(), nullable=True),
            _ts(),
        )
        op.create_index("ix_progress_checks_user_id", "progress_checks", ["user_id"])
        op.create_index("ix_progress_checks_user_created", "progress_checks", ["user_id", "created_at"])

    if not _exists("reports"):
        op.create_table(
            "reports",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("file_path", sa.String(), nullable=False),
            sa.Column("analysis_id", sa.String(), sa.ForeignKey("skin_analyses.id"), nullable=True),
            sa.Column("progress_id", sa.String(), sa.ForeignKey("progress_checks.id"), nullable=True),
            _ts(),
        )
        op.create_index("ix_reports_user_id", "reports", ["user_id"])
        op.create_index("ix_reports_analysis_id", "reports", ["analysis_id"])
        op.create_index("ix_reports_progress_id", "reports", ["progress_id"])

    if not _exists("chat_messages"):
        op.create_table(
            "chat_messages",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("role", sa.String(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            _ts(),
        )
        op.create_index("ix_chat_messages_user_id", "chat_messages", ["user_id"])
        op.create_index("ix_chat_messages_user_created", "chat_messages", ["user_id", "created_at"])


def downgrade() -> None:
    # The baseline is never downgraded automatically: it would delete user data.
    raise RuntimeError("Refusing to drop the baseline schema. Restore from backup instead.")
