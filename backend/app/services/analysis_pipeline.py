"""Analysis pipeline orchestrator — daily stock analysis execution.

Executes stages in sequence:
1. Data sync (incremental daily bars + northbound)
2. Feature computation
3. Model prediction
4. SHAP explanation
5. Ranking generation
"""

import asyncio
import uuid
from datetime import date, datetime, timezone

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.core.events import event_bus
from app.database import AsyncSessionLocal
from app.models.analysis_run import AnalysisRun

logger = structlog.get_logger()

STAGES = [
    "data_sync",
    "northbound_sync",
    "feature_engineering",
    "model_prediction",
    "shap_explanation",
    "ranking",
]


class AnalysisPipeline:
    def __init__(self):
        self._scheduler = AsyncIOScheduler()
        self._started = False
        self._current_run_id: str | None = None

    def start(self):
        if not self._started:
            self._scheduler.start()
            self._started = True

            self._scheduler.add_job(
                self._scheduled_run,
                trigger=CronTrigger(hour=17, minute=30, timezone="Asia/Shanghai"),
                id="analysis_pipeline_daily",
                replace_existing=True,
            )

            from app.services.data_sync_service import data_sync_service
            data_sync_service.register_schedules(self._scheduler)

            logger.info("analysis_pipeline.started")

    def stop(self):
        if self._started:
            self._scheduler.shutdown(wait=False)
            self._started = False
            logger.info("analysis_pipeline.stopped")

    async def trigger(self, trigger_type: str = "manual") -> str:
        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        asyncio.create_task(self._run_pipeline(run_id, trigger_type))
        return run_id

    async def _scheduled_run(self):
        if not _is_trading_day():
            logger.info("analysis_pipeline.skipped_non_trading_day")
            await self._record_skip()
            return
        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        await self._run_pipeline(run_id, "scheduled")

    async def _run_pipeline(self, run_id: str, trigger_type: str):
        self._current_run_id = run_id
        started_at = datetime.now(timezone.utc)
        stages_status = {}

        async with AsyncSessionLocal() as db:
            run = AnalysisRun(
                run_id=run_id,
                trigger_type=trigger_type,
                started_at=started_at,
                status="running",
                stages={},
            )
            db.add(run)
            await db.commit()

        for stage in STAGES:
            stages_status[stage] = {"status": "running", "started_at": datetime.now(timezone.utc).isoformat()}
            await self._update_run(run_id, stages=stages_status)
            await self._publish_progress(stage, "running")

            try:
                await self._execute_stage(stage)
                stages_status[stage]["status"] = "done"
                stages_status[stage]["finished_at"] = datetime.now(timezone.utc).isoformat()
                await self._update_run(run_id, stages=stages_status)
                await self._publish_progress(stage, "done")
            except Exception as e:
                logger.error("analysis_pipeline.stage_failed", stage=stage, error=str(e))
                stages_status[stage]["status"] = "failed"
                stages_status[stage]["error"] = str(e)
                stages_status[stage]["finished_at"] = datetime.now(timezone.utc).isoformat()
                await self._update_run(run_id, stages=stages_status, status="failed",
                                       finished_at=datetime.now(timezone.utc),
                                       error=f"Stage '{stage}' failed: {e}")
                await self._publish_progress(stage, "failed")
                self._current_run_id = None
                return

        await self._update_run(run_id, status="done", finished_at=datetime.now(timezone.utc))
        await event_bus.publish(event_bus.TOPIC_RANKING_READY, {
            "run_id": run_id, "date": str(date.today()), "message": "每日排名已更新",
        })
        logger.info("analysis_pipeline.completed", run_id=run_id)
        self._current_run_id = None

    async def _execute_stage(self, stage: str):
        if stage == "data_sync":
            from app.services.data_sync_service import data_sync_service
            await data_sync_service.sync_daily_bars_incremental()
        elif stage == "northbound_sync":
            from app.services.data_sync_service import data_sync_service
            await data_sync_service.sync_northbound_flow()
        elif stage == "feature_engineering":
            from app.services.feature_engine import FeatureEngine
            fe = FeatureEngine()
            await fe.compute_all_factors(date.today())
        elif stage == "model_prediction":
            from app.services.ml_model import ml_model_service
            result = await ml_model_service.predict(date.today())
            if result is None:
                logger.warning("analysis_pipeline.no_active_model")
                return
        elif stage == "shap_explanation":
            from app.services.ml_model import ml_model_service
            await ml_model_service.explain_predictions(date.today())
        elif stage == "ranking":
            from app.services.ranking_service import generate_daily_ranking
            async with AsyncSessionLocal() as db:
                await generate_daily_ranking(db, date.today())
                await db.commit()
        else:
            logger.warning("analysis_pipeline.unknown_stage", stage=stage)

    async def _update_run(self, run_id: str, **kwargs):
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(AnalysisRun).where(AnalysisRun.run_id == run_id))
            run = result.scalar_one_or_none()
            if run:
                for key, value in kwargs.items():
                    setattr(run, key, value)
                await db.commit()

    async def _publish_progress(self, stage: str, status: str):
        try:
            await event_bus.publish(event_bus.TOPIC_ANALYSIS_PROGRESS, {
                "stage": stage, "status": status, "run_id": self._current_run_id,
            })
        except Exception:
            pass

    async def _record_skip(self):
        async with AsyncSessionLocal() as db:
            run = AnalysisRun(
                run_id=f"skip_{date.today().isoformat()}",
                trigger_type="scheduled",
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc),
                status="skipped",
                error="non_trading_day",
                stages={},
            )
            db.add(run)
            await db.commit()


def _is_trading_day(d: date | None = None) -> bool:
    if d is None:
        d = date.today()
    if d.weekday() >= 5:
        return False
    return True


analysis_pipeline = AnalysisPipeline()
