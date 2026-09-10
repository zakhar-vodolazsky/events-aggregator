"""Track local updates without overwriting provider timestamps.

Revision ID: 8e9a214c7b30
Revises: 5c3bd19387d6
"""

import sqlalchemy as sa

from alembic import op

revision = "8e9a214c7b30"
down_revision = "5c3bd19387d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing rows start tracking local updates at migration time.
    for table, column in (
        ("places", "updated_at"),
        ("events", "updated_at"),
        ("events", "status_updated_at"),
    ):
        op.add_column(
            table,
            sa.Column(
                column, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
            ),
        )

    op.execute("""
        CREATE OR REPLACE FUNCTION set_changed_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = statement_timestamp();
            IF OLD.status IS DISTINCT FROM NEW.status THEN
                NEW.status_updated_at = NEW.updated_at;
            ELSE
                NEW.status_updated_at = OLD.status_updated_at;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION set_changed_at_places()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = statement_timestamp();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION set_changed_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.changed_at = NOW();
            IF OLD.status IS DISTINCT FROM NEW.status THEN
                NEW.status_changed_at = NOW();
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION set_changed_at_places()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.changed_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.drop_column("events", "status_updated_at")
    op.drop_column("events", "updated_at")
    op.drop_column("places", "updated_at")
