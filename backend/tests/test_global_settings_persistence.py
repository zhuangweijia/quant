import pytest
from sqlalchemy.dialects.sqlite import dialect as sqlite_dialect

from app.models.setting import Setting
from app.schemas.settings import SystemParams
from app.services.settings_service import save_system_params


def params(analysis_time="17:00"):
    return SystemParams(
        data_retention_days=90,
        alert_retention_days=90,
        model_train_window_days=756,
        model_val_window_days=126,
        forward_return_days=5,
        forward_return_threshold=0.02,
        model_ic_threshold=0.02,
        stock_universe="csi300",
        analysis_time=analysis_time,
    )


def test_setting_model_has_a_unique_partial_index_for_global_keys():
    index = next(
        (item for item in Setting.__table__.indexes if item.name == "uq_settings_global_cat_key"),
        None,
    )

    assert index is not None
    assert index.unique is True
    assert str(index.dialect_options["postgresql"]["where"]) == "user_id IS NULL"


@pytest.mark.asyncio
async def test_system_params_use_atomic_upsert_and_remain_unique():
    class EmptyResult:
        def scalar_one_or_none(self):
            return None

        def scalars(self):
            return self

        def all(self):
            return []

    class FakeSession:
        def __init__(self):
            self.dialect = sqlite_dialect()
            self.statements = []

        def get_bind(self):
            return type("Bind", (), {"dialect": self.dialect})()

        async def execute(self, statement):
            self.statements.append(statement)
            return EmptyResult()

        def add(self, _setting):
            return None

        async def flush(self):
            return None

    db = FakeSession()
    await save_system_params(db, params())
    await save_system_params(db, params("18:15"))

    compiled = [str(statement.compile(dialect=db.dialect)) for statement in db.statements]
    assert sum("INSERT INTO settings" in statement for statement in compiled) == 2
    assert sum("ON CONFLICT" in statement for statement in compiled) == 2
