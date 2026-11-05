"""Security hardening: user roles, analysis track/model versions, rate limits,
hashed password-reset tokens.

Revision ID: 0002_security_hardening
Revises: 0001_baseline
Create Date: 2026-10-31
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_security_hardening"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if "role" not in _columns("users"):
        with op.batch_alter_table("users") as batch:
            batch.add_column(sa.Column("role", sa.String(), nullable=False, server_default="user"))

    analysis_cols = _columns("skin_analyses")
    with op.batch_alter_table("skin_analyses") as batch:
        if "analysis_track" not in analysis_cols:
            batch.add_column(sa.Column("analysis_track", sa.String(), nullable=True))
        if "model_version" not in analysis_cols:
            batch.add_column(sa.Column("model_version", sa.String(), nullable=True))
        if "gate_version" not in analysis_cols:
            batch.add_column(sa.Column("gate_version", sa.String(), nullable=True))

    # Historical analyses were produced by Model A without an input gate.
    op.execute(
        "UPDATE skin_analyses SET analysis_track = 'facial_concerns' "
        "WHERE analysis_track IS NULL"
    )
    op.execute(
        "UPDATE skin_analyses SET model_version = 'facial-concerns-effnetb0-v1 (legacy, no input gate)' "
        "WHERE model_version IS NULL"
    )

    # Reset tokens were stored in clear text before this revision. They are
    # short-lived, so simply invalidate any outstanding ones.
    op.execute("UPDATE password_reset_tokens SET used = 1 WHERE used = 0" if op.get_bind().dialect.name == "sqlite"
               else "UPDATE password_reset_tokens SET used = TRUE WHERE used = FALSE")

    if not sa.inspect(op.get_bind()).has_table("rate_limit_events"):
        op.create_table(
            "rate_limit_events",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("bucket", sa.String(), nullable=False),
            sa.Column("key_hash", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index(
            "ix_rate_limit_bucket_key_created",
            "rate_limit_events",
            ["bucket", "key_hash", "created_at"],
        )


def downgrade() -> None:
    op.drop_index("ix_rate_limit_bucket_key_created", table_name="rate_limit_events")
    op.drop_table("rate_limit_events")

    with op.batch_alter_table("skin_analyses") as batch:
        batch.drop_column("gate_version")
        batch.drop_column("model_version")
        batch.drop_column("analysis_track")

    with op.batch_alter_table("users") as batch:
        batch.drop_column("role")
