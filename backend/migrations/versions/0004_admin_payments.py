"""Order payment status (cash-on-delivery tracking) for the admin panel.

Revision ID: 0004_admin_payments
Revises: 0003_shop
Create Date: 2026-11-02
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_admin_payments"
down_revision = "0003_shop"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("orders")}
    if "payment_status" not in columns:
        with op.batch_alter_table("orders") as batch:
            batch.add_column(
                sa.Column("payment_status", sa.String(), nullable=False, server_default="unpaid")
            )
        op.create_index("ix_orders_payment_status", "orders", ["payment_status"])


def downgrade() -> None:
    op.drop_index("ix_orders_payment_status", table_name="orders")
    with op.batch_alter_table("orders") as batch:
        batch.drop_column("payment_status")
