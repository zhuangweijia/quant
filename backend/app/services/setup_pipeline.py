import asyncio
import uuid
from copy import deepcopy
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Protocol

from sqlalchemy import select, update
from sqlalchemy.orm.attributes import flag_modified

from app.database import AsyncSessionLocal
from app.models.model_version import ModelVersion
from app.models.setup_run import SetupRun
from app.models.stock import Stock

SETUP_STAGES = [
    "constituents",
    "daily_bars",
    "fundamentals",
    "validation",
    "training",
    "activation",
    "analysis",
]


class SetupStore(Protocol):
    async def get_running_run_id(self) -> str | None: ...
    async def create_run(self, run_id: str) -> None: ...
    async def start_stage(self, run_id: str, stage: str) -> None: ...
    async def update_stage(self, run_id: str, stage: str, **progress) -> None: ...
    async def complete_stage(self, run_id: str, stage: str, **result) -> None: ...
    async def fail_run(self, run_id: str, stage: str, error: str) -> None: ...
    async def complete_run(self, run_id: str) -> None: ...
    async def list_pending_symbols(self) -> list[str]: ...
    async def mark_stock_synced(self, symbol: str) -> None: ...
    async def get_active_model_version(self) -> str | None: ...
    async def get_reusable_model_version(self) -> str | None: ...
    async def interrupt_running(self) -> int: ...


class SqlAlchemySetupStore:
    async def get_running_run_id(self) -> str | None:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(SetupRun.run_id)
                .where(SetupRun.status == "running")
                .order_by(SetupRun.started_at.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()

    async def create_run(self, run_id: str) -> None:
        async with AsyncSessionLocal() as db:
            db.add(
                SetupRun(
                    run_id=run_id,
                    status="running",
                    stages={},
                    started_at=datetime.now(UTC),
                )
            )
            await db.commit()

    async def _update_stages(self, run_id: str, stage: str, values: dict) -> None:
        async with AsyncSessionLocal() as db:
            run = await db.get(SetupRun, run_id)
            if run is None:
                return
            stages = deepcopy(run.stages or {})
            stages.setdefault(stage, {}).update(values)
            run.stages = stages
            run.current_stage = stage
            flag_modified(run, "stages")
            await db.commit()

    async def start_stage(self, run_id: str, stage: str) -> None:
        await self._update_stages(
            run_id,
            stage,
            {
                "status": "running",
                "started_at": datetime.now(UTC).isoformat(),
            },
        )

    async def update_stage(self, run_id: str, stage: str, **progress) -> None:
        await self._update_stages(run_id, stage, progress)

    async def complete_stage(self, run_id: str, stage: str, **result) -> None:
        await self._update_stages(
            run_id,
            stage,
            {
                **result,
                "status": "done",
                "finished_at": datetime.now(UTC).isoformat(),
            },
        )

    async def fail_run(self, run_id: str, stage: str, error: str) -> None:
        summary = error[:1024]
        await self._update_stages(
            run_id,
            stage,
            {
                "status": "failed",
                "error": summary,
                "finished_at": datetime.now(UTC).isoformat(),
            },
        )
        async with AsyncSessionLocal() as db:
            run = await db.get(SetupRun, run_id)
            if run:
                run.status = "failed"
                run.error = summary
                run.finished_at = datetime.now(UTC)
                await db.commit()

    async def complete_run(self, run_id: str) -> None:
        async with AsyncSessionLocal() as db:
            run = await db.get(SetupRun, run_id)
            if run:
                run.status = "completed"
                run.current_stage = None
                run.finished_at = datetime.now(UTC)
                await db.commit()

    async def list_pending_symbols(self) -> list[str]:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Stock.symbol)
                .where(Stock.in_csi300.is_(True), Stock.last_synced_date.is_(None))
                .order_by(Stock.symbol)
            )
            return list(result.scalars().all())

    async def mark_stock_synced(self, symbol: str) -> None:
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(Stock).where(Stock.symbol == symbol).values(last_synced_date=date.today())
            )
            await db.commit()

    async def get_active_model_version(self) -> str | None:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ModelVersion.version).where(ModelVersion.is_active.is_(True)).limit(1)
            )
            return result.scalar_one_or_none()

    async def get_reusable_model_version(self) -> str | None:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ModelVersion)
                .where(ModelVersion.is_active.is_(False))
                .order_by(ModelVersion.trained_at.desc())
            )
            for model in result.scalars().all():
                if Path(model.file_path).is_file():
                    return model.version
            return None

    async def interrupt_running(self) -> int:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                update(SetupRun)
                .where(SetupRun.status == "running")
                .values(
                    status="interrupted",
                    finished_at=datetime.now(UTC),
                    error="后端服务重启，初始化已中断，请继续初始化",
                )
            )
            await db.commit()
            return result.rowcount or 0


class ModelSetupAdapter:
    async def train(self) -> dict:
        from app.services.ml_model import ml_model_service

        return await ml_model_service.train()

    async def activate(self, version: str) -> None:
        from app.services.ml_model import ml_model_service

        async with AsyncSessionLocal() as db:
            await ml_model_service.activate_model(db, version)
            await db.commit()


class SetupPipeline:
    def __init__(self, store, data_sync, model_service, analysis):
        self.store = store
        self.data_sync = data_sync
        self.model_service = model_service
        self.analysis = analysis
        self._lock = asyncio.Lock()
        self._task: asyncio.Task | None = None

    async def start(self, wait: bool = False) -> str:
        async with self._lock:
            running = await self.store.get_running_run_id()
            if running:
                return running

            run_id = f"setup_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
            await self.store.create_run(run_id)
            self._task = asyncio.create_task(self._run(run_id))

        if wait:
            await self._task
        return run_id

    async def interrupt_stale_runs(self) -> int:
        return await self.store.interrupt_running()

    async def _run_stage(self, run_id: str, stage: str, operation):
        await self.store.start_stage(run_id, stage)
        try:
            result = await operation()
            details = {
                key: value
                for key, value in (result or {}).items()
                if key not in {"run_id", "status", "error"}
            }
            await self.store.complete_stage(run_id, stage, **details)
            return result
        except Exception as exc:
            await self.store.fail_run(run_id, stage, str(exc))
            raise

    async def _run(self, run_id: str) -> None:
        try:

            async def constituents():
                result = await self.data_sync.sync_csi300_constituents()
                if not result.get("success"):
                    raise RuntimeError(result.get("error", "成分股同步失败"))
                return result

            await self._run_stage(run_id, "constituents", constituents)

            await self.store.start_stage(run_id, "daily_bars")
            try:
                symbols = await self.store.list_pending_symbols()
                succeeded = 0
                failed = 0
                for current, symbol in enumerate(symbols, 1):
                    result = await self.data_sync.sync_daily_bars_full(symbol)
                    if result.get("success"):
                        succeeded += 1
                        await self.store.mark_stock_synced(symbol)
                    else:
                        failed += 1
                    await self.store.update_stage(
                        run_id,
                        "daily_bars",
                        current=current,
                        total=len(symbols),
                        succeeded=succeeded,
                        failed=failed,
                        symbol=symbol,
                    )
                await self.store.complete_stage(
                    run_id,
                    "daily_bars",
                    current=len(symbols),
                    total=len(symbols),
                    succeeded=succeeded,
                    failed=failed,
                )
            except Exception as exc:
                await self.store.fail_run(run_id, "daily_bars", str(exc))
                raise

            async def fundamentals():
                result = await self.data_sync.sync_fundamentals()
                if not result.get("success", True):
                    raise RuntimeError(result.get("error", "基本面同步失败"))
                return result

            await self._run_stage(run_id, "fundamentals", fundamentals)

            async def validation():
                result = await self.data_sync.validate_data_integrity()
                if result.get("total", 0) <= 0:
                    raise RuntimeError("数据完整性校验失败：没有可用股票数据")
                return result

            await self._run_stage(run_id, "validation", validation)

            active_version = await self.store.get_active_model_version()
            version = active_version

            async def training():
                nonlocal version
                if version:
                    return {"version": version, "reused": True}
                version = await self.store.get_reusable_model_version()
                if version:
                    return {"version": version, "reused": True}
                result = await self.model_service.train()
                version = result.get("version")
                if not version:
                    raise RuntimeError("模型训练未返回版本号")
                return result

            await self._run_stage(run_id, "training", training)

            async def activation():
                if not active_version:
                    await self.model_service.activate(version)
                return {"version": version, "reused": bool(active_version)}

            await self._run_stage(run_id, "activation", activation)

            async def analysis():
                result = await self.analysis.run_and_wait("setup")
                if result.get("status") != "done":
                    raise RuntimeError(result.get("error", "今日分析失败"))
                if result.get("prediction_count", 0) <= 0:
                    raise RuntimeError("今日分析完成，但没有生成预测数据")
                return result

            await self._run_stage(run_id, "analysis", analysis)
            await self.store.complete_run(run_id)
        except Exception:
            return


def _create_setup_pipeline() -> SetupPipeline:
    from app.services.analysis_pipeline import analysis_pipeline
    from app.services.data_sync_service import data_sync_service

    return SetupPipeline(
        SqlAlchemySetupStore(),
        data_sync_service,
        ModelSetupAdapter(),
        analysis_pipeline,
    )


setup_pipeline = _create_setup_pipeline()
