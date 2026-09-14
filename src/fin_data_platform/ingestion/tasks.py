"""Sync job 注册：把 Sync Engine 挂到 Runtime（最小：单标的日线）。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Engine

from fin_data_platform.ingestion.daily_bar import DATASET, sync_daily_bar
from fin_data_platform.runtime.models import JobKind
from fin_data_platform.runtime.registry import (
    JobContext,
    JobResult,
    TaskRegistry,
    TaskSpec,
)


def register_daily_bar_task(
    registry: TaskRegistry,
    engine: Engine,
    hub: Any,
    *,
    code: str,
    source: Any = None,
    schedule: str | None = None,
    priority: int = 100,
    max_attempts: int = 3,
) -> TaskSpec:
    """注册单标的日线同步任务（``scope=code``；窗口由调度或手动意图提供）。"""
    job_id = f"sync.{DATASET}.{code}"

    def executor(context: JobContext) -> JobResult:
        if context.window_start is None or context.window_end is None:
            raise ValueError("sync 任务需要窗口（window_start / window_end）")
        if context.scope and context.scope != code:
            raise ValueError(
                f"intent scope 与注册代码不一致: {context.scope!r} != {code!r}"
            )
        result = sync_daily_bar(
            engine,
            hub,
            code=code,
            start=context.window_start,
            end=context.window_end,
            source=source,
        )
        return JobResult(rows_written=result.rows_written)

    return registry.register(
        TaskSpec(
            job_id=job_id,
            kind=JobKind.SYNC.value,
            dataset=DATASET,
            executor=executor,
            schedule=schedule,
            priority=priority,
            max_attempts=max_attempts,
            scope=code,
        )
    )
