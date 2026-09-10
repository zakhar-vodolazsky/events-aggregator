"""Keep registration history when a provider ticket ID is reused."""

import sqlalchemy as sa

from alembic import op

revision = "f812d064ba31"
down_revision = "dd072595dfeb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("provider_ticket_id", sa.UUID(), nullable=True))
    op.execute("UPDATE tickets SET provider_ticket_id = id")
    op.alter_column("tickets", "provider_ticket_id", nullable=False)
    op.drop_constraint("uq_ticket_event_seat", "tickets", type_="unique")
    op.create_index(
        "uq_ticket_active_seat",
        "tickets",
        ["event_id", "seat"],
        unique=True,
        postgresql_where=sa.text("NOT is_revoked"),
    )


def downgrade() -> None:
    # Refuse to silently discard history if the old uniqueness rule can no longer hold.
    op.create_unique_constraint("uq_ticket_event_seat", "tickets", ["event_id", "seat"])
    op.drop_index("uq_ticket_active_seat", table_name="tickets")
    op.drop_column("tickets", "provider_ticket_id")
