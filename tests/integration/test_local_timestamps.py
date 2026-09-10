# PostgreSQL trigger test; enable with RUN_DB_TESTS=1

import asyncio
import importlib.util
import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

pytestmark = pytest.mark.skipif(os.getenv("RUN_DB_TESTS") != "1", reason="Opt-in local DB test")


def apply_migration(connection, filename, direction="upgrade"):
    path = Path(__file__).resolve().parents[2] / "alembic" / "versions" / filename
    spec = importlib.util.spec_from_file_location("migration_under_test", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load migration: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with Operations.context(MigrationContext.configure(connection)):
        getattr(module, direction)()


def test_local_timestamps():
    asyncio.run(check_local_timestamps())


async def check_local_timestamps():
    from app.core.config import get_settings

    url = make_url(get_settings().database_url)
    assert url.host in {"localhost", "127.0.0.1", "::1"}, "Test requires local PostgreSQL"
    engine = create_async_engine(url, hide_parameters=True)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                schema = "test_timestamps_" + uuid4().hex
                await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
                await connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
                for filename in (
                    "57cc8980a41a_create_tables.py",
                    "5c3bd19387d6_add_changed_at_triggers.py",
                    "8e9a214c7b30_local_update_timestamps.py",
                ):
                    await connection.run_sync(apply_migration, filename)

                await connection.execute(
                    text("""
                    INSERT INTO events (
                        id, name, event_time, registration_deadline, status,
                        number_of_visitors, seats, changed_at, status_changed_at,
                        updated_at, status_updated_at
                    ) VALUES (
                        '550e8400-e29b-41d4-a716-446655440000', 'Test', NOW(), NOW(),
                        'new', 0, 0, '2000-01-01', '2000-01-02', '2000-01-03', '2000-01-04'
                    )
                """)
                )
                before = (await connection.execute(text("SELECT * FROM events"))).mappings().one()
                await connection.execute(
                    text("""
                    UPDATE events SET name = 'Renamed', status_updated_at = NOW()
                """)
                )
                renamed = (await connection.execute(text("SELECT * FROM events"))).mappings().one()
                assert renamed["updated_at"] > before["updated_at"]
                assert renamed["status_updated_at"] == before["status_updated_at"]

                await connection.execute(text("UPDATE events SET status = 'published'"))
                changed = (await connection.execute(text("SELECT * FROM events"))).mappings().one()
                assert changed["status_updated_at"] > renamed["status_updated_at"]
                assert changed["status_updated_at"] == changed["updated_at"]
                await connection.execute(text("UPDATE events SET status = 'published'"))
                same = (await connection.execute(text("SELECT * FROM events"))).mappings().one()
                assert same["status_updated_at"] == changed["status_updated_at"]
                for row in (renamed, changed, same):
                    assert row["changed_at"] == before["changed_at"]
                    assert row["status_changed_at"] == before["status_changed_at"]

                await connection.execute(
                    text("""
                    INSERT INTO places (id, name, changed_at, updated_at)
                    VALUES ('650e8400-e29b-41d4-a716-446655440001', 'Place',
                            '2000-01-01', '2000-01-02')
                """)
                )
                place_before = (
                    (await connection.execute(text("SELECT * FROM places"))).mappings().one()
                )
                await connection.execute(text("UPDATE places SET name = 'Renamed'"))
                place_after = (
                    (await connection.execute(text("SELECT * FROM places"))).mappings().one()
                )
                assert place_after["updated_at"] > place_before["updated_at"]
                assert place_after["changed_at"] == place_before["changed_at"]
                await connection.run_sync(
                    apply_migration, "8e9a214c7b30_local_update_timestamps.py", "downgrade"
                )
                await connection.execute(text("UPDATE events SET status = 'new'"))
                await connection.execute(text("UPDATE places SET name = 'Restored'"))
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()
