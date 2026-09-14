"""FinDataRuntime 领域模型（doc-20 §4）。

- :class:`JobKind` / :class:`JobStatus`：任务类别与状态机取值；
- :class:`JobDef` / :class:`JobDependency`：声明式任务定义与依赖（镜像到 ``meta.*``）；
- :class:`JobIntent`：调度意图（幂等键 + 窗口 + 版本维度）；
- :class:`JobRun`：一次执行记录（状态权威在 ``meta.job_runs``）；
- :class:`Watermark`：数据集 / 分区水位。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class JobKind(StrEnum):
    SYNC = "sync"
    BACKFILL = "backfill"
    IMPORT = "import"
    DERIVE = "derive"
    BUILD_RM = "build_rm"
    QUALITY = "quality"
    CACHE_INVALIDATE = "cache_invalidate"
    EXPORT = "export"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD = "dead"
    INTERRUPTED = "interrupted"
    CANCELLED = "cancelled"


class DependencyCondition(StrEnum):
    ON_SUCCESS = "on_success"
    ON_COMPLETE = "on_complete"
    ALWAYS = "always"


#: 终态（不再变化）
TERMINAL_STATUSES = frozenset(
    {JobStatus.SUCCEEDED.value, JobStatus.DEAD.value, JobStatus.CANCELLED.value}
)
#: 可被 WorkerPool 领取的状态
CLAIMABLE_STATUSES = frozenset({JobStatus.QUEUED.value, JobStatus.RETRYING.value})
#: 依赖门控视为「已放行」的父状态（condition=on_success）
SUCCESS_STATUSES = frozenset({JobStatus.SUCCEEDED.value})


@dataclass(frozen=True, slots=True)
class JobDef:
    job_id: str
    kind: str
    dataset: str
    schedule: str | None = None
    priority: int = 100
    max_attempts: int = 3
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class JobDependency:
    parent_job: str
    child_job: str
    condition: str = DependencyCondition.ON_SUCCESS.value


@dataclass(frozen=True, slots=True)
class JobIntent:
    """一次可执行请求；``job_key`` 由 :func:`fin_data_platform.runtime.keys.job_key` 生成。"""

    kind: str
    job_id: str
    dataset: str
    scope: str = ""
    window_start: date | None = None
    window_end: date | None = None
    version_dimension: str | None = None
    priority: int = 100
    max_attempts: int = 3


@dataclass(frozen=True, slots=True)
class JobRun:
    run_id: int
    job_key: str
    job_id: str
    kind: str
    dataset: str
    scope: str
    status: str
    attempt: int
    max_attempts: int
    priority: int
    scheduled_at: datetime
    window_start: date | None = None
    window_end: date | None = None
    version_dimension: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    rows_written: int | None = None
    error: str | None = None
    request_id: str | None = None
    worker: str | None = None


@dataclass(frozen=True, slots=True)
class Watermark:
    dataset: str
    scope: str = ""
    watermark_time: datetime | None = None
