"""add_changed_at_triggers

Revision ID: 5c3bd19387d6
Revises: 57cc8980a41a
"""

from alembic import op

revision = "5c3bd19387d6"
down_revision = "57cc8980a41a"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
        CREATE TRIGGER trg_events_set_changed_at
        BEFORE UPDATE ON events
        FOR EACH ROW
        EXECUTE FUNCTION set_changed_at();
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

    op.execute("""
        CREATE TRIGGER trg_places_set_changed_at
        BEFORE UPDATE ON places
        FOR EACH ROW
        EXECUTE FUNCTION set_changed_at_places();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_events_set_changed_at ON events;")
    op.execute("DROP FUNCTION IF EXISTS set_changed_at();")
    op.execute("DROP TRIGGER IF EXISTS trg_places_set_changed_at ON places;")
    op.execute("DROP FUNCTION IF EXISTS set_changed_at_places();")
