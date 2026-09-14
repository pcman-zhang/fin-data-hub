"""FinDataRuntime：控制面 Runtime（doc-20 已定稿）。

角色分层（Scheduler / Dispatcher / WorkerPool）、声明式任务与依赖、``meta.*``
状态权威、可拆进程入口；数据语义仍由数据字典与平台核心承载。
"""

from fin_data_platform.runtime.app import RuntimeApp, default_registry
from fin_data_platform.runtime.calendar import HubTradeCalendar, TradeCalendar
from fin_data_platform.runtime.config import ROLES, RuntimeConfig
from fin_data_platform.runtime.health import ReadinessReport, readiness
from fin_data_platform.runtime.keys import (
    VERSIONED_KINDS,
    job_key,
    validate_version_dimension,
)
from fin_data_platform.runtime.models import (
    CLAIMABLE_STATUSES,
    TERMINAL_STATUSES,
    DependencyCondition,
    JobDef,
    JobDependency,
    JobIntent,
    JobKind,
    JobRun,
    JobStatus,
    Watermark,
)
from fin_data_platform.runtime.registry import (
    JobContext,
    JobExecutor,
    JobResult,
    TaskRegistry,
    TaskSpec,
)
from fin_data_platform.runtime.repository import (
    InMemoryMetaRepository,
    MetaRepository,
    SqlMetaRepository,
)
from fin_data_platform.runtime.roles import Dispatcher, Scheduler, WorkerPool
from fin_data_platform.runtime.schema import SCHEMA as META_SCHEMA
from fin_data_platform.runtime.windows import WatermarkWindowProvider

__all__ = [
    "CLAIMABLE_STATUSES",
    "DependencyCondition",
    "Dispatcher",
    "HubTradeCalendar",
    "InMemoryMetaRepository",
    "JobContext",
    "JobDef",
    "JobDependency",
    "JobExecutor",
    "JobIntent",
    "JobKind",
    "JobResult",
    "JobRun",
    "JobStatus",
    "META_SCHEMA",
    "MetaRepository",
    "ROLES",
    "ReadinessReport",
    "RuntimeApp",
    "RuntimeConfig",
    "Scheduler",
    "SqlMetaRepository",
    "TERMINAL_STATUSES",
    "TaskRegistry",
    "TaskSpec",
    "TradeCalendar",
    "VERSIONED_KINDS",
    "Watermark",
    "WatermarkWindowProvider",
    "WorkerPool",
    "default_registry",
    "job_key",
    "readiness",
    "validate_version_dimension",
]
