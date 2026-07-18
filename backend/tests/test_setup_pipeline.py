import pytest

from app.services.setup_pipeline import SetupPipeline


class FakeStore:
    def __init__(self, pending_symbols=None):
        self.runs = {}
        self.pending_symbols = list(pending_symbols or ["000001", "000002"])
        self.active_model = None
        self.reusable_model = None
        self.interrupted = 0

    async def get_running_run_id(self):
        for run_id, run in self.runs.items():
            if run["status"] == "running":
                return run_id
        return None

    async def create_run(self, run_id):
        self.runs[run_id] = {"status": "running", "stages": {}, "error": None}

    async def start_stage(self, run_id, stage):
        self.runs[run_id]["stages"][stage] = {"status": "running"}

    async def update_stage(self, run_id, stage, **progress):
        self.runs[run_id]["stages"][stage].update(progress)

    async def complete_stage(self, run_id, stage, **result):
        self.runs[run_id]["stages"][stage].update(status="done", **result)

    async def fail_run(self, run_id, stage, error):
        self.runs[run_id]["status"] = "failed"
        self.runs[run_id]["error"] = error
        self.runs[run_id]["stages"][stage].update(status="failed", error=error)

    async def complete_run(self, run_id):
        self.runs[run_id]["status"] = "completed"

    async def list_pending_symbols(self):
        return list(self.pending_symbols)

    async def mark_stock_synced(self, symbol):
        self.pending_symbols.remove(symbol)

    async def get_active_model_version(self):
        return self.active_model

    async def get_reusable_model_version(self):
        return self.reusable_model

    async def interrupt_running(self):
        count = 0
        for run in self.runs.values():
            if run["status"] == "running":
                run["status"] = "interrupted"
                count += 1
        self.interrupted += count
        return count


class FakeDataSync:
    def __init__(self):
        self.calls = []

    async def sync_csi300_constituents(self):
        self.calls.append("constituents")
        return {"success": True, "total": 2, "new": 2}

    async def sync_daily_bars_full(self, symbol):
        self.calls.append(f"daily_bars:{symbol}")
        return {"success": True, "symbol": symbol, "rows": 100}

    async def sync_fundamentals(self):
        self.calls.append("fundamentals")
        return {"success": True, "total": 2, "cached": 2}

    async def validate_data_integrity(self):
        self.calls.append("validation")
        return {"total": 2, "warnings": 0}


class RaisingDailyBarSync(FakeDataSync):
    async def sync_daily_bars_full(self, symbol):
        raise RuntimeError(f"行情源不可用: {symbol}")


class FakeModel:
    def __init__(self, activation_error=None):
        self.calls = []
        self.param_calls = []
        self.runtime_params = object()
        self.activation_error = activation_error

    async def load_params(self):
        self.calls.append("load_params")
        return self.runtime_params

    async def train(self, params):
        self.param_calls.append(("training", params))
        self.calls.append("training")
        return {"version": "model_v1", "ic": 0.05, "val_accuracy": 0.6}

    async def activate(self, version, params):
        self.param_calls.append(("activation", params))
        self.calls.append(f"activation:{version}")
        if self.activation_error:
            raise ValueError(self.activation_error)


class FakeAnalysis:
    def __init__(self, predictions=2):
        self.calls = []
        self.predictions = predictions

    async def run_and_wait(self, trigger_type):
        self.calls.append(f"analysis:{trigger_type}")
        return {"run_id": "analysis_1", "status": "done", "prediction_count": self.predictions}


@pytest.mark.asyncio
async def test_setup_pipeline_runs_all_stages_in_order():
    store = FakeStore()
    data = FakeDataSync()
    model = FakeModel()
    analysis = FakeAnalysis()
    pipeline = SetupPipeline(store, data, model, analysis)

    run_id = await pipeline.start(wait=True)

    assert store.runs[run_id]["status"] == "completed", store.runs[run_id]
    assert list(store.runs[run_id]["stages"]) == [
        "constituents",
        "daily_bars",
        "fundamentals",
        "validation",
        "training",
        "activation",
        "analysis",
    ]
    assert store.runs[run_id]["stages"]["daily_bars"]["current"] == 2
    assert data.calls == [
        "constituents",
        "daily_bars:000001",
        "daily_bars:000002",
        "fundamentals",
        "validation",
    ]
    assert model.calls == ["load_params", "training", "activation:model_v1"]
    assert analysis.calls == ["analysis:setup"]


@pytest.mark.asyncio
async def test_setup_pipeline_reuses_one_model_snapshot():
    model = FakeModel()
    pipeline = SetupPipeline(FakeStore(), FakeDataSync(), model, FakeAnalysis())

    await pipeline.start(wait=True)

    assert model.param_calls == [
        ("training", model.runtime_params),
        ("activation", model.runtime_params),
    ]


@pytest.mark.asyncio
async def test_setup_pipeline_returns_existing_running_run():
    store = FakeStore()
    store.runs["setup_existing"] = {"status": "running", "stages": {}, "error": None}
    data = FakeDataSync()
    pipeline = SetupPipeline(store, data, FakeModel(), FakeAnalysis())

    run_id = await pipeline.start(wait=True)

    assert run_id == "setup_existing"
    assert data.calls == []


@pytest.mark.asyncio
async def test_setup_pipeline_stops_when_model_fails_quality_gate():
    store = FakeStore()
    pipeline = SetupPipeline(
        store,
        FakeDataSync(),
        FakeModel("模型验证不达标: IC=0.01 < 阈值 0.02"),
        FakeAnalysis(),
    )

    run_id = await pipeline.start(wait=True)

    assert store.runs[run_id]["status"] == "failed"
    assert store.runs[run_id]["stages"]["activation"]["status"] == "failed"
    assert "模型验证不达标" in store.runs[run_id]["error"]
    assert "analysis" not in store.runs[run_id]["stages"]


@pytest.mark.asyncio
async def test_setup_pipeline_marks_stale_runs_interrupted():
    store = FakeStore()
    store.runs["setup_stale"] = {"status": "running", "stages": {}, "error": None}
    pipeline = SetupPipeline(store, FakeDataSync(), FakeModel(), FakeAnalysis())

    assert await pipeline.interrupt_stale_runs() == 1
    assert store.runs["setup_stale"]["status"] == "interrupted"


@pytest.mark.asyncio
async def test_setup_pipeline_persists_daily_bar_stage_exception():
    store = FakeStore(pending_symbols=["000001"])
    pipeline = SetupPipeline(store, RaisingDailyBarSync(), FakeModel(), FakeAnalysis())

    run_id = await pipeline.start(wait=True)

    assert store.runs[run_id]["status"] == "failed"
    assert store.runs[run_id]["stages"]["daily_bars"]["status"] == "failed"
    assert "行情源不可用" in store.runs[run_id]["error"]
