import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import MetaData, create_engine, inspect, select

BASE_REVISION = "c2d4e6f8a0b1"
CONSTRAINT_REVISION = "d5f0a1b2c3d4"


def _script_directory() -> ScriptDirectory:
    backend = Path(__file__).parents[1]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "alembic"))
    return ScriptDirectory.from_config(config)


def _run_revision(connection, revision, direction):
    revision_module = revision.module
    original_op = revision_module.op
    revision_module.op = Operations(MigrationContext.configure(connection))
    try:
        getattr(revision_module, direction)()
    finally:
        revision_module.op = original_op


def test_constraint_violations_successor_upgrade_backfills_and_downgrades(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'advice-migration.db'}")
    scripts = _script_directory()
    base = scripts.get_revision(BASE_REVISION)
    successor = scripts.get_revision(CONSTRAINT_REVISION)

    assert successor.down_revision == BASE_REVISION

    with engine.begin() as connection:
        _run_revision(connection, base, "upgrade")
        assert "constraint_violations" not in {
            column["name"] for column in inspect(connection).get_columns("daily_advices")
        }

        metadata = MetaData()
        metadata.reflect(connection, only=["daily_advices"], resolve_fks=False)
        advice_table = metadata.tables["daily_advices"]
        advice_id = uuid4().hex
        connection.execute(
            advice_table.insert().values(
                id=advice_id,
                user_id=uuid4().hex,
                portfolio_id=uuid4().hex,
                profile_id=uuid4().hex,
                source_snapshot_id=uuid4().hex,
                signal_date=date(2026, 7, 17),
                version=1,
                status="ready",
                model_version="model-v1",
                data_date=date(2026, 7, 17),
                current_exposure=Decimal("0.2"),
                target_exposure=Decimal("0.3"),
                estimated_cash=Decimal("7000"),
                generated_at=datetime(2026, 7, 17, 9, tzinfo=UTC),
                created_at=datetime(2026, 7, 17, 9, tzinfo=UTC),
                updated_at=datetime(2026, 7, 17, 9, tzinfo=UTC),
            )
        )

        _run_revision(connection, successor, "upgrade")
        columns = {
            column["name"]: column
            for column in inspect(connection).get_columns("daily_advices")
        }
        assert columns["constraint_violations"]["nullable"] is False
        assert columns["constraint_violations"]["default"] is not None

        upgraded = MetaData()
        upgraded.reflect(connection, only=["daily_advices"], resolve_fks=False)
        value = connection.scalar(
            select(upgraded.tables["daily_advices"].c.constraint_violations).where(
                upgraded.tables["daily_advices"].c.id == advice_id
            )
        )
        assert json.loads(value) == [] if isinstance(value, str) else value == []

        _run_revision(connection, successor, "downgrade")
        assert "constraint_violations" not in {
            column["name"] for column in inspect(connection).get_columns("daily_advices")
        }

    engine.dispose()
