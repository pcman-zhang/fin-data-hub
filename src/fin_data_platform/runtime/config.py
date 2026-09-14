"""Runtime 配置（凭证与 DSN 由调用方 / 环境注入，不落仓库；doc-20 §3）。"""

from __future__ import annotations

import os
from dataclasses import dataclass

from fin_data_platform.storage.config import StorageConfig

#: 角色入口（runtime / runtime-scheduler / runtime-worker）
RuntimeRole = str  # all | scheduler | worker

ROLES = ("all", "scheduler", "worker")


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    storage: StorageConfig
    role: RuntimeRole = "all"
    worker_count: int = 2
    #: Scheduler 到期计算间隔（秒）
    tick_interval: float = 1.0
    #: WorkerPool 轮询间隔（秒）
    worker_interval: float = 0.2
    #: 背压：全局 queued/retrying 上限（超过则 Dispatcher 暂不入队）
    max_queued: int = 100
    #: 启动检查开关（fail fast；doc-20 §3.4）
    check_dictionary: bool = True
    check_schema: bool = True

    @classmethod
    def from_env(
        cls,
        *,
        role: RuntimeRole = "all",
        worker_count: int = 2,
        tick_interval: float = 1.0,
        worker_interval: float = 0.2,
        max_queued: int = 100,
        check_dictionary: bool = True,
        check_schema: bool = True,
        host_override: str | None = None,
    ) -> RuntimeConfig:
        """由 ``DATABASE_*`` 环境变量构建（``FDP_DATABASE_HOST`` 可覆盖主机）。"""
        if role not in ROLES:
            raise ValueError(f"role 非法: {role!r}（可选: {', '.join(ROLES)}）")
        return cls(
            storage=StorageConfig.from_env(
                host_override=host_override or os.environ.get("FDP_DATABASE_HOST")
            ),
            role=role,
            worker_count=worker_count,
            tick_interval=tick_interval,
            worker_interval=worker_interval,
            max_queued=max_queued,
            check_dictionary=check_dictionary,
            check_schema=check_schema,
        )
