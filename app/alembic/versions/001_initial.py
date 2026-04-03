"""initial schema and seed data

Revision ID: 001
Revises:
Create Date: 2026-04-03 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Sequences ──────────────────────────────────────────────────────────
    op.execute("CREATE SEQUENCE IF NOT EXISTS order_id_seq START WITH 50000")

    # ── Countries ──────────────────────────────────────────────────────────
    op.create_table(
        "countries",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("prefix", sa.String(10), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("prefix"),
    )

    # ── US States ───────────────────────────────────────────────────────────
    op.create_table(
        "us_states",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("country_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["country_id"], ["countries.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── Plans ───────────────────────────────────────────────────────────────
    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("ram_gb", sa.Integer(), nullable=False),
        sa.Column("cpu_cores", sa.Integer(), nullable=False),
        sa.Column("ssd_gb", sa.Integer(), nullable=False),
        sa.Column("price_usd", sa.Numeric(10, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── OS Options ──────────────────────────────────────────────────────────
    op.create_table(
        "os_options",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── Validities ──────────────────────────────────────────────────────────
    op.create_table(
        "validities",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("label", sa.String(50), nullable=False),
        sa.Column("days", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── Settings ────────────────────────────────────────────────────────────
    op.create_table(
        "settings",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("value", sa.Text(), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )

    # ── Message Templates ───────────────────────────────────────────────────
    op.create_table(
        "message_templates",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    # ── Telegram Users ──────────────────────────────────────────────────────
    op.create_table(
        "telegram_users",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("first_name", sa.String(200), nullable=True),
        sa.Column("last_name", sa.String(200), nullable=True),
        sa.Column("username", sa.String(200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_id"),
    )

    # ── User States ─────────────────────────────────────────────────────────
    op.create_table(
        "user_states",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("telegram_user_id", sa.Integer(), nullable=False),
        sa.Column("current_step", sa.String(100), nullable=True),
        sa.Column("selected_country_id", sa.Integer(), nullable=True),
        sa.Column("selected_state_id", sa.Integer(), nullable=True),
        sa.Column("selected_plan_id", sa.Integer(), nullable=True),
        sa.Column("selected_os_id", sa.Integer(), nullable=True),
        sa.Column("selected_validity_id", sa.Integer(), nullable=True),
        sa.Column("customer_email", sa.String(255), nullable=True),
        sa.Column("current_order_id", sa.Integer(), nullable=True),
        sa.Column("data_json", sa.JSON(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["telegram_user_id"], ["telegram_users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_user_id"),
    )

    # ── Orders ──────────────────────────────────────────────────────────────
    op.create_table(
        "orders",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("nextval('order_id_seq')"),
        ),
        sa.Column("telegram_user_id", sa.Integer(), nullable=False),
        sa.Column("country_id", sa.Integer(), nullable=False),
        sa.Column("us_state_id", sa.Integer(), nullable=True),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("os_option_id", sa.Integer(), nullable=False),
        sa.Column("validity_id", sa.Integer(), nullable=False),
        sa.Column("customer_email", sa.String(255), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending_payment",
                "processing",
                "completed",
                "cancelled_expired",
                "manual_review",
                name="orderstatus",
            ),
            nullable=False,
            server_default="pending_payment",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["country_id"], ["countries.id"]),
        sa.ForeignKeyConstraint(["os_option_id"], ["os_options.id"]),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"]),
        sa.ForeignKeyConstraint(["telegram_user_id"], ["telegram_users.id"]),
        sa.ForeignKeyConstraint(["us_state_id"], ["us_states.id"]),
        sa.ForeignKeyConstraint(["validity_id"], ["validities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── Payments ─────────────────────────────────────────────────────────────
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("cryptomus_invoice_id", sa.String(100), nullable=True),
        sa.Column("amount_usd", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "paid_on_time",
                "paid_late",
                "expired",
                name="paymentstatus",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id"),
    )

    # ── Deliveries ───────────────────────────────────────────────────────────
    op.create_table(
        "deliveries",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("ip_address", sa.String(100), nullable=False),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("password", sa.String(200), nullable=False),
        sa.Column("expiry_date", sa.String(20), nullable=False),
        sa.Column(
            "delivered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── Webhook Events ────────────────────────────────────────────────────────
    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column(
            "processed", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── SEED DATA ─────────────────────────────────────────────────────────────

    # Countries
    op.execute("""
        INSERT INTO countries (name, prefix, is_active, sort_order) VALUES
        ('United States', 'US', true, 1),
        ('United Kingdom', 'UK', true, 2),
        ('Australia', 'AU', true, 3),
        ('Canada', 'CA', true, 4),
        ('Germany', 'GE', true, 5),
        ('India', 'IN', true, 6),
        ('Singapore', 'SG', true, 7),
        ('Netherlands', 'NL', true, 8)
    """)

    # US States (country_id = 1 for US)
    op.execute("""
        INSERT INTO us_states (country_id, name, is_active, sort_order) VALUES
        (1, 'New York', true, 1),
        (1, 'San Francisco', true, 2),
        (1, 'Florida', true, 3),
        (1, 'New Jersey', true, 4)
    """)

    # Plans
    op.execute("""
        INSERT INTO plans (name, ram_gb, cpu_cores, ssd_gb, price_usd, is_active, sort_order) VALUES
        ('Basic',    2,  1,  40,  9.99, true, 1),
        ('Standard', 4,  2,  60, 14.99, true, 2),
        ('Advanced', 8,  4,  80, 24.99, true, 3),
        ('Premium',  16, 6, 120, 39.99, true, 4),
        ('Ultimate', 32, 8, 200, 59.99, true, 5),
        ('Business', 64, 16, 400, 99.99, true, 6)
    """)

    # OS Options
    op.execute("""
        INSERT INTO os_options (name, is_active, sort_order) VALUES
        ('Windows 11 Pro', true, 1),
        ('Windows 10 Pro', true, 2),
        ('Windows Server 2019', true, 3),
        ('Windows Server 2022', true, 4)
    """)

    # Validities
    op.execute("""
        INSERT INTO validities (label, days, is_active) VALUES
        ('1 Month', 30, true)
    """)

    # Settings
    op.execute("""
        INSERT INTO settings (key, value, description) VALUES
        ('fulfillment_eta', 'Completed within 1–4 hours', 'Fulfillment ETA shown to users after payment'),
        ('support_contact', '@support', 'Support contact shown in messages'),
        ('maintenance_mode', 'false', 'Set to true to block new orders')
    """)

    # Message Templates
    op.execute(r"""
        INSERT INTO message_templates (slug, name, body_text) VALUES
        ('welcome', 'Welcome Message', '👋 Welcome to RDP Aura Bot!
Purchase premium RDP access with crypto payments.
Click below to start your order.'),
        ('order_summary', 'Order Summary', '📋 Order Summary

🌍 Country: {country}
🗺️ State: {state}
📦 Plan: {plan}
💻 OS: {os}
📅 Validity: {validity}
📧 Email: {email}
💰 Price: ${price}

Order #{order_id}'),
        ('payment_created', 'Payment Created', '💳 Invoice created for Order #{order_id}

Amount: ${amount} USD
Expires in 2 hours.

Click the Pay Now button below to complete your payment.'),
        ('processing', 'Processing', '✅ Order #{order_id} — Payment Received!

Status: Processing
{fulfillment_eta}

We''ll send your RDP credentials shortly.'),
        ('completed', 'Completed / Delivery', '🎉 Order #{order_id} — Completed!

Your RDP Access Details:
🌐 IP: {ip}
👤 User: {username}
🔑 Pass: {password}
📅 Expires: {expiry_date}

Save these credentials securely!'),
        ('manual_review', 'Manual Review', '⏳ Order #{order_id} — Under Review

Your payment was received but requires manual verification.
Our team will review it shortly. Contact {support_contact} for help.'),
        ('cancelled', 'Cancelled', '❌ Order #{order_id} has been cancelled.')
    """)


def downgrade() -> None:
    op.drop_table("webhook_events")
    op.drop_table("deliveries")
    op.drop_table("payments")
    op.drop_table("orders")
    op.drop_table("user_states")
    op.drop_table("telegram_users")
    op.drop_table("message_templates")
    op.drop_table("settings")
    op.drop_table("validities")
    op.drop_table("os_options")
    op.drop_table("plans")
    op.drop_table("us_states")
    op.drop_table("countries")
    op.execute("DROP SEQUENCE IF EXISTS order_id_seq")
    op.execute("DROP TYPE IF EXISTS orderstatus")
    op.execute("DROP TYPE IF EXISTS paymentstatus")
