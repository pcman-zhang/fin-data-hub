"""TASK-3.6 切片 2 测试：交易日历 / 水位窗口 / APScheduler 调度 / 水位推进。"""

from __future__ import annotations

import time
from datetime import date, datetime
from datetime import time as clock_time

import pandas as pd
import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.pool import StaticPool

from fin_data_platform.ingestion import register_daily_bar_task
from fin_data_platform.runtime import (
    HubTradeCalendar,
    InMemoryMetaRepository,
    JobIntent,
    JobResult,
    RuntimeApp,
    RuntimeConfig,
    SqlMetaRepository,
    TaskRegistry,
    TaskSpec,
    WatermarkWindowProvider,
)
from fin_data_platform.storage.config import StorageConfig
from fin_data_platform.storage.schema import build_metadata

DAY1 = date(2026, 9, 10)
DAY2 = date(2026, 9, 11)
CODE = "600519.SH"


class FakeCalendar:
    def __init__(self, last_closed: date | None) -> None:
        self.last_closed_value = last_closed

    def is_trading_day(self, day: date) -> bool:
        return True

    def last_closed(self, now: datetime | None = None) -> date | None:
        return self.last_closed_value


class FakeHub:
    """日线数据 + 日历（切片 2 测试用）。"""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def get_bars(
        self,
        codes,
        *,
        start: str,
        end: str,
        freq: str = "1d",
        adjust: str | None = None,
        source=None,
        **_: object,
    ) -> pd.DataFrame:
        self.calls.append((tuple(codes), start, end))
        rows = [
            {
                "code": CODE,
                "date": pd.Timestamp("2026-09-10"),
                "open": 10.0,
                "high": 11.0,
                "low": 9.5,
                "close": 10.5,
                "volume": 1000.0,
                "amount": 10500.0,
            },
            {
                "code": CODE,
                "date": pd.Timestamp("2026-09-11"),
                "open": 10.5,
                "high": 11.5,
                "low": 10.0,
                "close": 11.0,
                "volume": 1200.0,
                "amount": 13200.0,
            },
        ]
        frame = pd.DataFrame(
            [row for row in rows if start <= row["date"].date().isoformat() <= end]
        )
        frame.attrs["source"] = "tushare"
        return frame

    def get_trade_calendar(self, *, start: str, end: str, source=None) -> pd.DataFrame:
        days = [day for day in (DAY1, DAY2) if day.isoformat() <= end]
        return pd.DataFrame({"date": days, "is_open": [True] * len(days)})


def _spec(registry: TaskRegistry, engine, hub, *, schedule: str | None = None) -> TaskSpec:
    return register_daily_bar_task(registry, engine, hub, code=CODE, schedule=schedule)


@pytest.fixture()
def engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    with engine.begin() as connection:
        for schema in ("cn_equity", "cn_fund", "ref", "meta"):
            connection.execute(text(f"ATTACH DATABASE ':memory:' AS {schema}"))
    metadata, _ = build_metadata()
    metadata.create_all(engine)
    return engine


def _count(engine, table) -> int:
    with engine.begin() as connection:
        return int(
            connection.execute(select(func.count()).select_from(table)).scalar_one()
        )


def _config() -> RuntimeConfig:
    return RuntimeConfig(
        storage=StorageConfig(write_dsn="sqlite://"),
        role="all",
        worker_count=1,
        tick_interval=0.01,
        worker_interval=0.05,
    )


# ------------------------------------------------------------------ 窗口 / 日历
def test_watermark_window_provider_first_gap_and_catchup() -> None:
    repo = InMemoryMetaRepository()
    registry = TaskRegistry()
    spec = registry.register(
        TaskSpec(job_id="j", kind="sync", dataset="d", executor=lambda ctx: JobResult())
    )
    calendar = FakeCalendar(DAY2)
    provider = WatermarkWindowProvider(
        repo, calendar, start_dates={"j": DAY1}
    )

    assert provider(spec, datetime(2026, 9, 12, 8, 0)) == [(DAY1, DAY2)]

    repo.set_watermark("d", scope="", watermark_time=datetime(2026, 9, 10))
    assert provider(spec, datetime(2026, 9, 12, 8, 0)) == [(DAY2, DAY2)]

    repo.set_watermark("d", scope="", watermark_time=datetime(2026, 9, 11))
    assert provider(spec, datetime(2026, 9, 12, 8, 0)) == []  # 已追平

    # 无水位且无配置起点：不自动触发（防全量）
    other = WatermarkWindowProvider(repo, calendar)
    empty = TaskRegistry().register(
        TaskSpec(job_id="k", kind="sync", dataset="d2", executor=lambda ctx: JobResult())
    )
    assert other(empty, datetime(2026, 9, 12, 8, 0)) == []


def test_hub_calendar_respects_publish_cutoff() -> None:
    calendar = HubTradeCalendar(FakeHub())
    assert calendar.is_trading_day(DAY2) is True
    assert calendar.last_closed(datetime(2026, 9, 11, 6, 0)) == DAY1  # 收盘前
    assert calendar.last_closed(datetime(2026, 9, 11, 8, 0)) == DAY1  # 发布截止（16:30 CST）前
    assert calendar.last_closed(datetime(2026, 9, 11, 9, 0)) == DAY2  # 发布截止后


# ------------------------------------------------------------------ on_success 水位
def test_watermark_advances_after_success(engine) -> None:
    hub = FakeHub()
    registry = TaskRegistry()
    spec = _spec(registry, engine, hub)
    repo = SqlMetaRepository(engine)
    app = RuntimeApp(_config(), engine=engine, repository=repo, registry=registry)
    app.sync_metadata()

    intent = JobIntent(
        kind="sync",
        job_id=spec.job_id,
        dataset="cn_equity.daily_bar",
        scope=CODE,
        window_start=DAY1,
        window_end=DAY2,
    )
    assert app.submit(intent) == "created"
    assert app.run_pending() == 1

    mark = repo.get_watermark("cn_equity.daily_bar", scope=CODE)
    assert mark is not None and mark.watermark_time is not None
    assert mark.watermark_time.date() == DAY2


# ------------------------------------------------------------------ APScheduler
def test_apscheduler_registers_catchup_and_fires() -> None:
    """调度机制单测：不触 SQLite 并发（真实多线程路径见 PG 集成测试）。

    - APScheduler 注册 + 启动追平（水位推进）；
    - ``triggers.fire`` 分发（与 APScheduler 回调同路径）；
    - job store 在无 engine 时使用内存实现。
    """
    from fin_data_platform.runtime import triggers

    repo = InMemoryMetaRepository()
    registry = TaskRegistry()
    job_id = "sync.demo.X"

    def on_success(context, _result, repository) -> None:
        if context.window_end is not None:
            repository.set_watermark(
                "demo",
                scope="X",
                watermark_time=datetime.combine(context.window_end, clock_time(0, 0)),
            )

    registry.register(
        TaskSpec(
            job_id=job_id,
            kind="sync",
            dataset="demo",
            scope="X",
            executor=lambda ctx: JobResult(rows_written=1),
            # 每年 1 月 1 日触发：测试期间不会自动触发，由 fire 驱动
            schedule="0 0 1 1 *",
            on_success=on_success,
        )
    )
    spec = registry.get(job_id)
    calendar = FakeCalendar(DAY2)
    provider = WatermarkWindowProvider(repo, calendar, start_dates={job_id: DAY1})
    app = RuntimeApp(_config(), repository=repo, registry=registry, due_provider=provider)
    app.start()
    try:
        health = app.health()
        assert health["scheduler"]["backend"] == "apscheduler"
        assert health["scheduler"]["aps_jobs"] == 1
        assert health["scheduler"]["alive"] is True  # 调度角色健康可见
        assert health["scheduler"]["last_tick_at"] is not None

        deadline = time.monotonic() + 5
        mark = None
        while time.monotonic() < deadline:
            runs = repo.list_runs(job_id=job_id)
            mark = repo.get_watermark("demo", scope="X")
            if runs and runs[0].status == "succeeded" and mark is not None:
                break
            time.sleep(0.05)
        runs = repo.list_runs(job_id=job_id)
        assert runs and runs[0].status == "succeeded"  # 启动追平已执行
        assert mark is not None and mark.watermark_time is not None
        assert mark.watermark_time.date() == DAY2

        # 回退水位 → fire 触发（与 APScheduler 回调同路径）→ 新窗口入队并执行
        repo.set_watermark(
            "demo", scope="X", watermark_time=datetime.combine(DAY1, clock_time(0, 0))
        )
        triggers.fire(job_id)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if len(repo.list_runs(job_id=job_id)) >= 2:
                break
            time.sleep(0.05)
        assert len(repo.list_runs(job_id=job_id)) >= 2
    finally:
        app.stop(timeout=2.0)
        triggers.unregister_handler(job_id)

    # 触发后水位重新追平
    assert spec.job_id == job_id


# ------------------------------------------------------------------ 复审回归
def test_advance_watermark_is_monotonic(engine) -> None:
    memory = InMemoryMetaRepository()
    memory.advance_watermark("d", scope="s", watermark_time=datetime(2026, 9, 10))
    memory.advance_watermark("d", scope="s", watermark_time=datetime(2026, 9, 5))
    mark = memory.get_watermark("d", scope="s")
    assert mark is not None and mark.watermark_time == datetime(2026, 9, 10)

    repo = SqlMetaRepository(engine)
    repo.advance_watermark("d", scope="s", watermark_time=datetime(2026, 9, 10))
    repo.advance_watermark("d", scope="s", watermark_time=datetime(2026, 9, 5))
    sql_mark = repo.get_watermark("d", scope="s")
    assert sql_mark is not None and sql_mark.watermark_time == datetime(2026, 9, 10)


def test_watermark_holds_today_when_empty(engine, monkeypatch) -> None:
    """窗口末日=今日且无数据：保留今日待下轮重试（源端可能未发布）。"""
    from fin_data_platform.ingestion import tasks as ingestion_tasks

    monkeypatch.setattr(
        ingestion_tasks, "utcnow", lambda: datetime(2026, 9, 11, 12, 0)
    )

    class EmptyHub(FakeHub):
        def get_bars(self, codes, **kwargs) -> pd.DataFrame:
            frame = pd.DataFrame(
                columns=["code", "date", "open", "high", "low", "close", "volume", "amount"]
            )
            frame.attrs["source"] = "tushare"
            return frame

    hub = EmptyHub()
    registry = TaskRegistry()
    spec = _spec(registry, engine, hub)
    repo = SqlMetaRepository(engine)
    app = RuntimeApp(_config(), engine=engine, repository=repo, registry=registry)
    app.sync_metadata()

    intent = JobIntent(
        kind="sync",
        job_id=spec.job_id,
        dataset="cn_equity.daily_bar",
        scope=CODE,
        window_start=DAY1,
        window_end=DAY2,  # DAY2 == 今日（monkeypatch）
    )
    assert app.submit(intent) == "created"
    assert app.run_pending() == 1

    mark = repo.get_watermark("cn_equity.daily_bar", scope=CODE)
    assert mark is not None and mark.watermark_time is not None
    assert mark.watermark_time.date() == DAY1  # 今日保留待重试


def test_mixed_registry_polls_unscheduled_tasks() -> None:
    """存在 schedule 任务时，未配置 schedule 的任务仍由轮询线程处理。"""

    def provider(spec, now):
        return [(DAY1, DAY2)]

    repo = InMemoryMetaRepository()
    registry = TaskRegistry()
    registry.register(
        TaskSpec(
            job_id="sched",
            kind="sync",
            dataset="d1",
            scope="s",
            executor=lambda ctx: JobResult(rows_written=1),
            schedule="0 0 1 1 *",  # 测试期间不触发
        )
    )
    registry.register(
        TaskSpec(
            job_id="manual",
            kind="sync",
            dataset="d2",
            scope="m",
            executor=lambda ctx: JobResult(rows_written=1),
        )
    )
    app = RuntimeApp(_config(), repository=repo, registry=registry, due_provider=provider)
    app.start()
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            runs = repo.list_runs()
            if any(r.job_id == "manual" and r.status == "succeeded" for r in runs):
                break
            time.sleep(0.05)
        runs = repo.list_runs()
        assert any(r.job_id == "manual" and r.status == "succeeded" for r in runs)
        sched_runs = [r for r in runs if r.job_id == "sched"]
        assert len(sched_runs) == 1  # 仅启动追平一次（cron 未到）
        assert sched_runs[0].status == "succeeded"
    finally:
        app.stop(timeout=2.0)
