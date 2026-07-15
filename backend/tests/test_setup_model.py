from app.models.setup_run import SetupRun
from app.schemas.setup import SetupCounts, SetupStatusResponse


def test_setup_run_mapping_and_status_schema():
    assert SetupRun.__tablename__ == "setup_runs"
    assert [column.name for column in SetupRun.__table__.primary_key] == ["run_id"]
    assert SetupRun.__table__.c.status.default.arg == "running"

    response = SetupStatusResponse(
        readiness="uninitialized",
        counts=SetupCounts(stocks=0, daily_bars=0, models=0, today_predictions=0),
        active_model=None,
        run=None,
        can_start=True,
        can_run_analysis=False,
    )

    assert response.model_dump()["counts"]["daily_bars"] == 0
