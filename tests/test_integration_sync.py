"""真实单标的 sync 实验（默认跳过：``pytest -m integration``）。

依赖 ``TUSHARE_TOKEN`` 与 dev 数据库；断言以「增量」为准，可重复执行（不清库）。
"""

from __future__ import annotations

import os
import threading
from datetime import date

import pytest
from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.engine import Engine

from fin_data_platform.ingestion import register_daily_bar_task, sync_daily_bar
from fin_data_platform.registry.schema import entity, entity_code_history
from fin_data_platform.registry.store import EntityStore
from fin_data_platform.runtime import (
    JobIntent,
    RuntimeApp,
    RuntimeConfig,
    SqlMetaRepository,
    TaskRegistry,
)
from fin_data_platform.runtime.schema import job_runs
from fin_data_platform.storage import StorageConfig
from fin_data_platform.storage.migrations import upgrade
from fin_data_platform.storage.schema import build_metadata

pytestmark = pytest.mark.integration

CODE = "600519.SH"
FIRST_WINDOW = (date(2026, 9, 7), date(2026, 9, 11))
SECOND_WINDOW = (date(2026, 9, 1), date(2026, 9, 11))


@pytest.fixture(scope="module")
def engine() -> Engine:
    if not os.environ.get("DATABASE_USER"):
        pytest.skip("缺少 DATABASE_* 环境变量")
    if not os.environ.get("TUSHARE_TOKEN"):
        pytest.skip("缺少 TUSHARE_TOKEN")
    dsn = StorageConfig.from_env(
        host_override=os.environ.get("FDP_DATABASE_HOST")
    ).write_dsn
    upgrade(dsn, "head")
    engine = create_engine(dsn)
    yield engine
    engine.dispose()


def _hub():
    from fin_data_hub import FinDataHub, HubConfig, Source
    from fin_data_hub.config import TushareConfig

    hub = FinDataHub.from_config(
        HubConfig(tushare=TushareConfig(token=os.environ["TUSHARE_TOKEN"]))
    )
    return hub, Source.TUSHARE


def _count(engine: Engine, code: str) -> int:
    metadata, _ = build_metadata()
    table = metadata.tables["cn_equity.daily_bar"]
    with engine.begin() as connection:
        return int(
            connection.execute(
                select(func.count())
                .select_from(table)
                .join(entity, entity.c.entity_id == table.c.entity_id)
                .where(entity.c.code == code)
            ).scalar_one()
        )


def test_single_symbol_sync_experiment(engine: Engine) -> None:
    hub, source = _hub()
    before = _count(engine, CODE)

    first = sync_daily_bar(
        engine, hub, code=CODE, start=FIRST_WINDOW[0], end=FIRST_WINDOW[1], source=source
    )
    assert first.provider == "tushare"
    assert first.fetched >= 1
    assert first.rows_written <= first.fetched
    assert _count(engine, CODE) == before + first.rows_written

    # 重复窗口：值未变 → 幂等（无新版本、无新增行）
    again = sync_daily_bar(
        engine, hub, code=CODE, start=FIRST_WINDOW[0], end=FIRST_WINDOW[1], source=source
    )
    assert again.entity_id == first.entity_id
    assert again.rows_written == 0

    # 稳定主键：同一代码只有一行身份
    with engine.begin() as connection:
        identities = connection.execute(
            select(func.count()).select_from(entity).where(entity.c.code == CODE)
        ).scalar_one()
    assert int(identities) == 1

    # Runtime 任务闭环：扩窗补数（仅新增交易日行；重叠日不重复）
    registry = TaskRegistry()
    spec = register_daily_bar_task(registry, engine, hub, code=CODE, source=source)
    repo = SqlMetaRepository(engine)
    config = RuntimeConfig(
        storage=StorageConfig.from_env(
            host_override=os.environ.get("FDP_DATABASE_HOST")
        ),
        role="all",
        worker_count=1,
    )
    app = RuntimeApp(config, engine=engine, repository=repo, registry=registry)
    app.sync_metadata()

    before_run = _count(engine, CODE)
    intent = JobIntent(
        kind="sync",
        job_id=spec.job_id,
        dataset="cn_equity.daily_bar",
        scope=CODE,
        window_start=SECOND_WINDOW[0],
        window_end=SECOND_WINDOW[1],
    )
    # 清理该任务的既有运行记录：测试可重复执行（数据写入本身幂等）
    with engine.begin() as connection:
        connection.execute(delete(job_runs).where(job_runs.c.job_id == spec.job_id))
    assert app.submit(intent) == "created"
    assert app.run_pending() == 1
    runs = repo.list_runs(job_id=spec.job_id)
    assert runs[0].status == "succeeded"
    assert runs[0].rows_written is not None
    assert _count(engine, CODE) == before_run + int(runs[0].rows_written)


def test_concurrent_entity_allocation_is_unique(engine: Engine) -> None:
    """不同代码并发注册必须拿到不同 entity_id（全局分配锁回归）。"""
    codes = ["T999001.SH", "T999002.SZ"]
    with engine.begin() as connection:
        connection.execute(delete(entity).where(entity.c.code.in_(codes)))
        connection.execute(
            delete(entity_code_history).where(entity_code_history.c.code.in_(codes))
        )

    results: list[int] = []
    barrier = threading.Barrier(3)

    def allocate(code: str) -> None:
        barrier.wait()
        results.append(EntityStore(engine).ensure_entity(code=code, name="并发测试").entity_id)

    threads = [threading.Thread(target=allocate, args=(code,)) for code in codes]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join(timeout=10)

    assert len(results) == 2
    assert len(set(results)) == 2

    with engine.begin() as connection:
        connection.execute(delete(entity).where(entity.c.code.in_(codes)))
        connection.execute(
            delete(entity_code_history).where(entity_code_history.c.code.in_(codes))
        )
