"""create Phase 0 schema and seed sports"""

from alembic import op
import sqlalchemy as sa

revision = "0001_phase0"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    user_role = sa.Enum("PLAYER", "PROVIDER", name="user_role")
    booking_status = sa.Enum("PENDING", "CONFIRMED", "CANCELLED", name="booking_status")
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False, server_default="PLAYER"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "sports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
    )
    op.create_index("ix_sports_name", "sports", ["name"], unique=True)
    op.create_table(
        "provider_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("business_name", sa.String(150), nullable=False),
        sa.Column("bio", sa.Text()),
        sa.Column("phone", sa.String(30)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id"),
    )
    op.create_table(
        "venues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider_id", sa.Integer(), sa.ForeignKey("provider_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("address", sa.String(255), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
    )
    op.create_index("ix_venues_provider_id", "venues", ["provider_id"])
    op.create_index("ix_venues_city", "venues", ["city"])
    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider_id", sa.Integer(), sa.ForeignKey("provider_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("venue_id", sa.Integer(), sa.ForeignKey("venues.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("sport_id", sa.Integer(), sa.ForeignKey("sports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_sessions_provider_id", "sessions", ["provider_id"])
    op.create_index("ix_sessions_venue_id", "sessions", ["venue_id"])
    op.create_index("ix_sessions_sport_id", "sessions", ["sport_id"])
    op.create_index("ix_sessions_starts_at", "sessions", ["starts_at"])
    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", booking_status, nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("session_id", "player_id", name="uq_booking_session_player"),
    )
    op.create_index("ix_bookings_session_id", "bookings", ["session_id"])
    op.create_index("ix_bookings_player_id", "bookings", ["player_id"])
    op.create_index("ix_bookings_status", "bookings", ["status"])
    op.bulk_insert(sa.table("sports", sa.column("name", sa.String())), [
        {"name": "Cricket"},
        {"name": "Football"},
        {"name": "Badminton"},
        {"name": "Tennis"},
    ])


def downgrade() -> None:
    op.drop_table("bookings")
    op.drop_table("sessions")
    op.drop_table("venues")
    op.drop_table("provider_profiles")
    op.drop_table("sports")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    sa.Enum(name="booking_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="user_role").drop(op.get_bind(), checkfirst=True)
