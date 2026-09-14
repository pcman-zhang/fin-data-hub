"""FinDataRuntime 真实 PG 集成测试（默认跳过：``pytest -m integration``）。

覆盖：meta schema 迁移后仓储流程（创建 / 领取 / 完成 / 水位）与并发领取互斥
（PG advisory lock + ``SKIP LOCKED``）。
"""

from __future__ import annotations

import os
import threading
from datetime import date, datetime

import pytest
from sqlalchemy import create_engine, delete
from sqlalchemy.engine import Engine

from fin_data_platform.runtime import JobIntent, SqlMetaRepository
from fin_data_platform.runtime.schema import job_runs
from fin_data_platform.storage import StorageConfig
from fin_data_platform.storage.migrations import upgrade

pytestmark = pytest.mark.integration

DAY = date(2026, 9, 14)
JOB_ID = "it_runtime_demo"
DATASET = "cn_equity.daily_bar"


@pytest.fixture(scope="module")
def engine() -> Engine:
    if not os.environ.get("DATABASE_USER"):
        pytest.skip("缺少 DATABASE_* 环境变量")
    dsn = StorageConfig.from_env(
        host_override=os.environ.get("FDP_DATABASE_HOST")
    ).write_dsn
    upgrade(dsn, "head")
    engine = create_engine(dsn)
    yield engine
    with engine.begin() as connection:
        connection.execute(delete(job_runs).where(job_runs.c.job_id == JOB_ID))
    engine.dispose()


def _intent() -> JobIntent:
    return JobIntent(
        kind="sync",
        job_id=JOB_ID,
        dataset=DATASET,
        scope="it",
        window_start=DAY,
        window_end=DAY,
    )


def test_runtime_repository_roundtrip_on_postgres(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(delete(job_runs).where(job_runs.c.job_id == JOB_ID))
    repo = SqlMetaRepository(engine)
    run = repo.create_run(_intent())
    assert run is not None
    assert repo.create_run(_intent()) is None  # 幂等

    claimed = repo.claim_next(worker="it-worker")
    assert claimed is not None and claimed.run_id == run.run_id
    done = repo.succeed(claimed.run_id, rows_written=1)
    assert done.status == "succeeded"
    assert repo.count_queued() == 0

    mark = repo.set_watermark("cn_equity.it_demo", watermark_time=datetime(2026, 9, 14))
    assert mark.watermark_time == datetime(2026, 9, 14)


def test_concurrent_claim_exclusive_on_postgres(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(delete(job_runs).where(job_runs.c.job_id == JOB_ID))
    repo = SqlMetaRepository(engine)
    assert repo.create_run(_intent()) is not None

    results: list[object] = []
    barrier = threading.Barrier(3)

    def claim(name: str) -> None:
        barrier.wait()
        results.append(repo.claim_next(worker=name))

    threads = [
        threading.Thread(target=claim, args=(f"it-{index}",)) for index in range(2)
    ]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join(timeout=10)

    claimed = [run for run in results if run is not None]
    assert len(claimed) == 1  # 同一 (dataset, scope) 仅一个可领取
    repo.succeed(claimed[0].run_id)  # type: ignore[attr-defined]


def test_entrypoint_starts_on_postgres(engine: Engine) -> None:
    """入口可启动：readiness 通过后进入常驻，可被信号停止。"""
    import subprocess
    import sys
    import time

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "fin_data_platform.runtime",
            "--role",
            "worker",
            "--log-level",
            "WARNING",
        ],
        env=dict(os.environ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(2)
    process.terminate()
    _stdout, stderr = process.communicate(timeout=15)
    assert process.returncode in (0, -15)
    assert "readiness 未通过" not in stderr.decode("utf-8", errors="replace")
