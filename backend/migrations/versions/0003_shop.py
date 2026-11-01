"""Shop: products, cart items, orders, order items.

Revision ID: 0003_shop
Revises: 0002_security_hardening
Create Date: 2026-10-31
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_shop"
down_revision = "0002_security_hardening"
branch_labels = None
depends_on = None


def _exists(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def _ts(name: str = "created_at"):
    return sa.Column(name, sa.DateTime(timezone=True), nullable=False)


def upgrade() -> None:
    if not _exists("products"):
        op.create_table(
            "products",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("brand", sa.String(), nullable=False),
            sa.Column("category", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("size", sa.String(), nullable=True),
            sa.Column("ingredients_json", sa.Text(), nullable=False),
            sa.Column("ingredient_keys_json", sa.Text(), nullable=False),
            sa.Column("skin_types_json", sa.Text(), nullable=True),
            sa.Column("concerns_json", sa.Text(), nullable=True),
            sa.Column("price", sa.Float(), nullable=False),
            sa.Column("currency", sa.String(), nullable=False),
            sa.Column("price_source", sa.String(), nullable=True),
            sa.Column("price_checked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("stock", sa.Integer(), nullable=False),
            sa.Column("image_url", sa.String(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("is_sponsored", sa.Boolean(), nullable=False),
            _ts(),
            _ts("updated_at"),
        )
        op.create_index("ix_products_name", "products", ["name"])
        op.create_index("ix_products_brand", "products", ["brand"])
        op.create_index("ix_products_category", "products", ["category"])

    if not _exists("cart_items"):
        op.create_table(
            "cart_items",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("product_id", sa.String(), sa.ForeignKey("products.id"), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False),
            _ts(),
        )
        op.create_index("ix_cart_items_user_id", "cart_items", ["user_id"])
        op.create_index("ix_cart_items_product_id", "cart_items", ["product_id"])
        op.create_index("ux_cart_user_product", "cart_items", ["user_id", "product_id"], unique=True)

    if not _exists("orders"):
        op.create_table(
            "orders",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("payment_method", sa.String(), nullable=False),
            sa.Column("subtotal", sa.Float(), nullable=False),
            sa.Column("currency", sa.String(), nullable=False),
            sa.Column("shipping_name", sa.String(), nullable=False),
            sa.Column("shipping_phone", sa.String(), nullable=False),
            sa.Column("shipping_address", sa.Text(), nullable=False),
            sa.Column("shipping_city", sa.String(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            _ts(),
            _ts("updated_at"),
        )
        op.create_index("ix_orders_user_id", "orders", ["user_id"])
        op.create_index("ix_orders_status", "orders", ["status"])
        op.create_index("ix_orders_user_created", "orders", ["user_id", "created_at"])

    if not _exists("order_items"):
        op.create_table(
            "order_items",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("order_id", sa.String(), sa.ForeignKey("orders.id"), nullable=False),
            sa.Column("product_id", sa.String(), nullable=True),
            sa.Column("product_name", sa.String(), nullable=False),
            sa.Column("brand", sa.String(), nullable=False),
            sa.Column("unit_price", sa.Float(), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False),
            sa.Column("line_total", sa.Float(), nullable=False),
        )
        op.create_index("ix_order_items_order_id", "order_items", ["order_id"])
        op.create_index("ix_order_items_product_id", "order_items", ["product_id"])


def downgrade() -> None:
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("cart_items")
    op.drop_table("products")
