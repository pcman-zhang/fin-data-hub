"""调用与成本计量（线程安全、进程内内存）。

设计目标（见 doc-1 §3.4）：
- 记录每次源端调用的 ``source/endpoint/codes/latency/est_cost``；
- 按日统计调用次数与估算成本，支持配置预算与告警（warn / exceeded）；
- **不落盘**（与「本库不含存储层」一致），默认仅统计当前进程；
- 跨进程汇总由调用方通过 ``BudgetConfig.on_record`` 回调实现（写入自有
  DB / Redis / 指标系统）；本库不内置共享计数器。
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime

logger = logging.getLogger("fin_data_hub.usage")


@dataclass(frozen=True, slots=True)
class UsageRecord:
    source: str
    endpoint: str
    calls: int
    codes: tuple[str, ...]
    latency_ms: float
    est_cost: float
    day: str
    timestamp: float


@dataclass(frozen=True, slots=True)
class BudgetAlert:
    source: str
    metric: str  # "calls" | "cost"
    level: str  # "warn" | "exceeded"
    value: float
    limit: float
    day: str


@dataclass(frozen=True, slots=True)
class BudgetConfig:
    """预算配置。

    - ``calls_per_day`` / ``cost_per_day``：按 source 的日预算；
    - ``cost_table``：``"source.endpoint"`` → 单次成本（可选，另支持按 source 兜底）；
    - ``warn_ratio``：达到预算该比例时告警；
    - ``on_alert``：告警回调（可选）；
    - ``on_record``：每条记录回调（可选，跨进程汇总的集成点）。
    """

    calls_per_day: Mapping[str, int] = field(default_factory=dict)
    cost_per_day: Mapping[str, float] = field(default_factory=dict)
    cost_table: Mapping[str, float] = field(default_factory=dict)
    warn_ratio: float = 0.8
    on_alert: Callable[[BudgetAlert], None] | None = field(
        default=None, compare=False, repr=False
    )
    on_record: Callable[[UsageRecord], None] | None = field(
        default=None, compare=False, repr=False
    )


class UsageLedger:
    """按日聚合的调用/成本台账（线程安全）。"""

    def __init__(
        self,
        budget: BudgetConfig | None = None,
        *,
        clock: Callable[[], float] = time.time,
        max_records: int = 1000,
    ) -> None:
        self.budget = budget or BudgetConfig()
        self._clock = clock
        self._records: deque[UsageRecord] = deque(maxlen=max_records)
        self._calls: dict[tuple[str, str], int] = {}
        self._cost: dict[tuple[str, str], float] = {}
        self._alerts: list[BudgetAlert] = []
        self._fired: set[tuple[str, str, str, str]] = set()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ 记录
    def record(
        self,
        source: str,
        endpoint: str,
        *,
        calls: int = 1,
        codes: tuple[str, ...] = (),
        latency_ms: float = 0.0,
    ) -> UsageRecord:
        now = self._clock()
        day = datetime.fromtimestamp(now, UTC).strftime("%Y-%m-%d")
        unit_cost = self._unit_cost(source, endpoint)
        record = UsageRecord(
            source=source,
            endpoint=endpoint,
            calls=calls,
            codes=tuple(codes),
            latency_ms=latency_ms,
            est_cost=unit_cost * calls,
            day=day,
            timestamp=now,
        )
        with self._lock:
            self._calls[(day, source)] = self._calls.get((day, source), 0) + calls
            self._cost[(day, source)] = (
                self._cost.get((day, source), 0.0) + record.est_cost
            )
            self._records.append(record)
            self._check_budget(day, source)
        if self.budget.on_record is not None:
            try:
                self.budget.on_record(record)
            except Exception:  # noqa: BLE001 - 回调异常不影响主流程
                logger.exception("on_record 回调执行失败")
        return record

    def _unit_cost(self, source: str, endpoint: str) -> float:
        table = self.budget.cost_table
        if f"{source}.{endpoint}" in table:
            return float(table[f"{source}.{endpoint}"])
        return float(table.get(source, 0.0))

    def _check_budget(self, day: str, source: str) -> None:
        calls = self._calls.get((day, source), 0)
        cost = self._cost.get((day, source), 0.0)
        call_limit = self.budget.calls_per_day.get(source)
        if call_limit:
            self._alert_if_needed(day, source, "calls", calls, float(call_limit))
        cost_limit = self.budget.cost_per_day.get(source)
        if cost_limit:
            self._alert_if_needed(day, source, "cost", cost, float(cost_limit))

    def _alert_if_needed(
        self, day: str, source: str, metric: str, value: float, limit: float
    ) -> None:
        level = "exceeded" if value >= limit else (
            "warn" if value >= limit * self.budget.warn_ratio else None
        )
        if level is None:
            return
        key = (day, source, metric, level)
        if key in self._fired:
            return
        self._fired.add(key)
        alert = BudgetAlert(
            source=source, metric=metric, level=level, value=value, limit=limit, day=day
        )
        self._alerts.append(alert)
        logger.warning(
            "预算告警[%s] %s %s: %.2f / %.2f（%s）",
            level,
            source,
            metric,
            value,
            limit,
            day,
        )
        if self.budget.on_alert is not None:
            self.budget.on_alert(alert)

    # ------------------------------------------------------------------ 查询
    def summary(self) -> dict:
        with self._lock:
            day = datetime.fromtimestamp(self._clock(), UTC).strftime("%Y-%m-%d")
            sources: dict[str, dict[str, float | int]] = {}
            for (record_day, source), calls in self._calls.items():
                if record_day != day:
                    continue
                sources.setdefault(source, {"calls": 0, "cost": 0.0})
                sources[source]["calls"] = calls
            for (record_day, source), cost in self._cost.items():
                if record_day != day:
                    continue
                sources.setdefault(source, {"calls": 0, "cost": 0.0})
                sources[source]["cost"] = round(cost, 6)
            alerts = [
                {
                    "source": a.source,
                    "metric": a.metric,
                    "level": a.level,
                    "value": a.value,
                    "limit": a.limit,
                }
                for a in self._alerts
                if a.day == day
            ]
            return {
                "day": day,
                "sources": sources,
                "alerts": alerts,
                "records": len(self._records),
            }

    @property
    def records(self) -> tuple[UsageRecord, ...]:
        with self._lock:
            return tuple(self._records)
