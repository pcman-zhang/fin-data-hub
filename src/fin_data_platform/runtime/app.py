"""Runtime 编排：按角色启动 Scheduler / Dispatcher / WorkerPool（doc-20 §3.2）。"""

from __future__ import annotations

import os
import threading
from datetime import datetime
from typing import Any

from sqlalchemy import Engine

from fin_data_platform.runtime.config import RuntimeConfig
from fin_data_platform.runtime.health import ReadinessReport, readiness
from fin_data_platform.runtime.models import JobIntent
from fin_data_platform.runtime.registry import TaskRegistry
from fin_data_platform.runtime.repository import MetaRepository, SqlMetaRepository
from fin_data_platform.runtime.roles import (
    Dispatcher,
    DueProvider,
    Scheduler,
    WorkerPool,
)


class RuntimeApp:
    """Runtime 骨架：任务注册镜像、角色编排、健康与就绪检查。

    - ``role=all``：Scheduler + Dispatcher + WorkerPool 同进程；
    - ``role=scheduler``：仅调度与分发（可独立进程）；
    - ``role=worker``：仅执行（可独立进程）；三者仅经 PostgreSQL 协调。
    """

    def __init__(
        self,
        config: RuntimeConfig,
        *,
        engine: Engine | None = None,
        repository: MetaRepository | None = None,
        registry: TaskRegistry | None = None,
        due_provider: DueProvider | None = None,
    ) -> None:
        if repository is None and engine is None:
            raise ValueError("需要 engine 或 repository 之一")
        self._config = config
        self._engine = engine
        self._registry = registry or TaskRegistry()
        if repository is not None:
            self._repo: MetaRepository = repository
        else:
            assert engine is not None
            self._repo = SqlMetaRepository(engine)
        self._scheduler = Scheduler(self._registry, due_provider=due_provider)
        self._dispatcher = Dispatcher(
            self._repo, max_queued=config.max_queued
        )
        self._pool = WorkerPool(
            self._repo,
            self._registry,
            # 进程级前缀：停机超时回收仅命中本进程的 running 行
            name=f"worker-{os.getpid()}",
            workers=config.worker_count,
        )
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []

    # ------------------------------------------------------------ 生命周期
    def sync_metadata(self) -> None:
        """镜像任务定义与依赖到 ``meta.*``（注册校验失败即拒绝启动）。"""
        errors = self._registry.validate()
        if errors:
            raise ValueError("任务注册校验失败: " + "; ".join(errors))
        self._repo.sync_defs(self._registry.defs())
        self._repo.sync_dependencies(self._registry.dependencies())

    def start(self) -> None:
        self._stop.clear()
        self.sync_metadata()
        role = self._config.role
        if role in ("all", "scheduler"):
            thread = threading.Thread(
                target=self._scheduler.run,
                args=(self._stop, self._dispatcher.submit),
                kwargs={"interval": self._config.tick_interval},
                name="runtime-scheduler",
                daemon=True,
            )
            thread.start()
            self._threads.append(thread)
        if role in ("all", "worker"):
            self._pool.start(self._stop, interval=self._config.worker_interval)

    def stop(self, *, timeout: float = 5.0) -> None:
        self._stop.set()
        self._pool.stop(timeout=timeout)
        for thread in self._threads:
            thread.join(timeout=timeout)
        self._threads.clear()

    # ------------------------------------------------------------ 提交与查询
    def submit(self, intent: JobIntent) -> str:
        return self._dispatcher.submit(intent)

    def tick(self, now: datetime | None = None) -> list[JobIntent]:
        return self._scheduler.tick(now)

    def run_pending(self) -> int:
        """同步执行一轮可领取任务（测试 / 手动运维用）。"""
        executed = 0
        while self._pool.execute_once() is not None:
            executed += 1
        return executed

    # ------------------------------------------------------------ 健康
    def health(self) -> dict[str, Any]:
        return {
            "role": self._config.role,
            "scheduler": {
                "alive": self._scheduler.health.alive,
                "last_tick_at": self._scheduler.health.last_tick_at,
                "intents_emitted": self._scheduler.health.intents_emitted,
                "last_error": self._scheduler.health.last_error,
            },
            "dispatcher": {
                "last_dispatch_at": self._dispatcher.health.last_dispatch_at,
                "created": self._dispatcher.health.created,
                "duplicate": self._dispatcher.health.duplicate,
                "dependency_blocked": self._dispatcher.health.dependency_blocked,
                "backpressure_blocked": self._dispatcher.health.backpressure_blocked,
            },
            "workers": {
                "alive": self._pool.health.alive,
                "threads_alive": self._pool.alive_threads(),
                "busy": self._pool.health.busy,
                "executed": self._pool.health.executed,
                "last_completed_at": self._pool.health.last_completed_at,
                "last_error": self._pool.health.last_error,
            },
        }

    def readiness(self) -> ReadinessReport | None:
        if self._engine is None:
            return None
        return readiness(
            self._engine,
            dsn=self._config.storage.write_dsn,
            check_directory=self._config.check_dictionary,
            check_schema=self._config.check_schema,
        )


def default_registry() -> TaskRegistry:
    """默认任务注册表（骨架期为空；任务由 TASK-3.5 / 3.6 / 3.12 等注册）。"""
    return TaskRegistry()
