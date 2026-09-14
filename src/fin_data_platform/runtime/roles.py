"""角色分层（doc-20 §3.2）：Scheduler / Dispatcher / WorkerPool。

- **Scheduler**：按任务定义计算到期窗口并入队——只入队、不执行、不等待；
- **Dispatcher**：依赖门控（``meta.job_dependencies``）+ 背压（queued 上限）；
  优先级由 ``meta.job_runs`` 领取排序保证；
- **WorkerPool**：从 ``meta.job_runs`` 原子领取并执行；状态权威在元数据表；
- 三者仅经 :class:`~fin_data_platform.runtime.repository.MetaRepository` 协调，
  **无共享可变状态**，因此可拆进程（``runtime-scheduler`` / ``runtime-worker``）。
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date, datetime

from fin_data_platform.runtime._util import utcnow
from fin_data_platform.runtime.models import JobIntent, JobRun
from fin_data_platform.runtime.registry import JobContext, TaskRegistry, TaskSpec
from fin_data_platform.runtime.repository import MetaRepository

#: 到期窗口提供者：(spec, now) -> 需要执行的 (window_start, window_end) 序列
DueProvider = Callable[[TaskSpec, datetime], Iterable[tuple[date, date]]]

#: 入队结果
SUBMIT_CREATED = "created"
SUBMIT_DUPLICATE = "duplicate"
SUBMIT_DEPENDENCY = "dependency"
SUBMIT_BACKPRESSURE = "backpressure"


@dataclass(slots=True)
class SchedulerHealth:
    alive: bool = False
    last_tick_at: datetime | None = None
    intents_emitted: int = 0
    last_error: str | None = None


class Scheduler:
    """只做时间计算与入队；执行耗时与它无关（隔离原则）。"""

    def __init__(
        self,
        registry: TaskRegistry,
        *,
        due_provider: DueProvider | None = None,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self._registry = registry
        self._due_provider = due_provider
        self._clock = clock
        self.health = SchedulerHealth()

    def tick(self, now: datetime | None = None) -> list[JobIntent]:
        """计算本轮到期意图（无 due_provider 时返回空：仅手动触发）。"""
        moment = now or self._clock()
        intents: list[JobIntent] = []
        if self._due_provider is not None:
            for spec in self._registry:
                for window_start, window_end in self._due_provider(spec, moment):
                    intents.append(
                        self._registry.intent(
                            spec, window_start=window_start, window_end=window_end
                        )
                    )
        self.health.last_tick_at = moment
        self.health.intents_emitted += len(intents)
        return intents

    def run(
        self,
        stop: threading.Event,
        submit: Callable[[JobIntent], str],
        *,
        interval: float = 1.0,
    ) -> None:
        """后台循环：tick 后逐个非阻塞提交（submit 不得阻塞）。

        循环内兜底捕获仓储 / 提交异常：单次失败不终止调度角色（隔离原则）。
        """
        self.health.alive = True
        try:
            while not stop.is_set():
                try:
                    for intent in self.tick():
                        submit(intent)
                except Exception as exc:
                    self.health.last_error = f"{type(exc).__name__}: {exc}"
                stop.wait(interval)
        finally:
            self.health.alive = False


@dataclass(slots=True)
class DispatcherHealth:
    last_dispatch_at: datetime | None = None
    created: int = 0
    duplicate: int = 0
    dependency_blocked: int = 0
    backpressure_blocked: int = 0


class Dispatcher:
    """依赖门控 + 背压；幂等创建由仓储保证（重复提交安全）。"""

    def __init__(
        self,
        repository: MetaRepository,
        *,
        max_queued: int = 100,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self._repo = repository
        self._max_queued = max_queued
        self._clock = clock
        self._lock = threading.Lock()
        self.health = DispatcherHealth()

    def submit(self, intent: JobIntent) -> str:
        """尝试入队：返回 created / duplicate / dependency / backpressure。"""
        with self._lock:
            if self._repo.count_queued() >= self._max_queued:
                self.health.backpressure_blocked += 1
                self.health.last_dispatch_at = self._clock()
                return SUBMIT_BACKPRESSURE
            ready = self._repo.parents_ready(
                child_job=intent.job_id,
                scope=intent.scope,
                window_start=intent.window_start,
                window_end=intent.window_end,
            )
            if not ready:
                self.health.dependency_blocked += 1
                self.health.last_dispatch_at = self._clock()
                return SUBMIT_DEPENDENCY
            run = self._repo.create_run(intent)
            self.health.last_dispatch_at = self._clock()
            if run is None:
                self.health.duplicate += 1
                return SUBMIT_DUPLICATE
            self.health.created += 1
            return SUBMIT_CREATED


@dataclass(slots=True)
class WorkerHealth:
    alive: bool = False
    busy: int = 0
    last_completed_at: datetime | None = None
    last_error: str | None = None
    executed: int = 0


class WorkerPool:
    """从元数据原子领取并执行；进程内仅编排线程，状态全在 ``meta.job_runs``。"""

    def __init__(
        self,
        repository: MetaRepository,
        registry: TaskRegistry,
        *,
        name: str = "worker",
        workers: int = 2,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self._repo = repository
        self._registry = registry
        self._name = name
        self._workers = max(1, workers)
        self._clock = clock
        self._lock = threading.Lock()
        self.health = WorkerHealth()
        self._threads: list[threading.Thread] = []

    def execute_once(
        self, *, worker_id: str | None = None, now: datetime | None = None
    ) -> JobRun | None:
        """领取并执行一个任务；无可领取任务返回 ``None``。"""
        label = worker_id or self._name
        run = self._repo.claim_next(worker=label, now=now or self._clock())
        if run is None:
            return None
        with self._lock:
            self.health.busy += 1
        try:
            try:
                spec = self._registry.get(run.job_id)
            except KeyError:
                finished = self._repo.fail(
                    run.run_id, error=f"任务未注册: {run.job_id}"
                )
                with self._lock:
                    self.health.last_error = finished.error
                return finished
            context = JobContext(
                job_id=run.job_id, kind=run.kind, dataset=run.dataset, run=run
            )
            try:
                result = spec.executor(context)
                finished = self._repo.succeed(
                    run.run_id, rows_written=result.rows_written if result else 0
                )
            except Exception as exc:  # 执行异常不污染数据；状态回落元数据
                finished = self._repo.fail(
                    run.run_id, error=f"{type(exc).__name__}: {exc}"
                )
                with self._lock:
                    self.health.last_error = finished.error
            with self._lock:
                self.health.executed += 1
                self.health.last_completed_at = self._clock()
            return finished
        finally:
            with self._lock:
                self.health.busy = max(0, self.health.busy - 1)

    def start(self, stop: threading.Event, *, interval: float = 0.2) -> None:
        """启动工作线程（每个线程独立轮询领取）。"""
        self.health.alive = True

        def loop(index: int) -> None:
            label = f"{self._name}-{index}"
            while not stop.is_set():
                try:
                    self.execute_once(worker_id=label)
                except Exception as exc:
                    # 仓储 / 领取异常不终止线程（隔离原则；错误入健康输出）
                    with self._lock:
                        self.health.last_error = f"{type(exc).__name__}: {exc}"
                stop.wait(interval)

        for index in range(self._workers):
            thread = threading.Thread(
                target=loop, args=(index,), name=f"{self._name}-{index}", daemon=True
            )
            thread.start()
            self._threads.append(thread)

    def alive_threads(self) -> int:
        return sum(1 for thread in self._threads if thread.is_alive())

    def stop(self, timeout: float = 5.0) -> None:
        """等待线程退出；超时未退出的线程，其 running 行回收为 interrupted。"""
        for thread in self._threads:
            thread.join(timeout=timeout)
        stuck = self.alive_threads()
        if stuck:
            self._repo.interrupt_running(worker_prefix=self._name)
        self._threads.clear()
        self.health.alive = False
