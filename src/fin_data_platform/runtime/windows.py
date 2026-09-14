"""水位窗口计算（doc-20 §4.5 / §4.6，TASK-3.6 切片 2）。

由「水位 + 交易日历」推导待同步窗口：``(水位+1天, 最近已收盘交易日)``；
水位缺失时使用配置的首次起点；窗口为空表示已追平。断点恢复与补数共用该机制
（缺口即窗口），实际幂等由写入端保证。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import date, datetime, timedelta

from fin_data_platform.runtime._util import utcnow
from fin_data_platform.runtime.calendar import TradeCalendar
from fin_data_platform.runtime.registry import TaskSpec
from fin_data_platform.runtime.repository import MetaRepository


class WatermarkWindowProvider:
    """按任务给出到期窗口；实现 ``DueProvider`` 协议（spec, now）→ 窗口序列。"""

    def __init__(
        self,
        repository: MetaRepository,
        calendar: TradeCalendar,
        *,
        start_dates: Mapping[str, date] | None = None,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self._repo = repository
        self._calendar = calendar
        self._start_dates = dict(start_dates or {})
        self._clock = clock

    def __call__(
        self, spec: TaskSpec, now: datetime | None = None
    ) -> list[tuple[date, date]]:
        moment = now or self._clock()
        last_closed = self._calendar.last_closed(moment)
        if last_closed is None:
            return []
        mark = self._repo.get_watermark(spec.dataset, scope=spec.scope)
        if mark is not None and mark.watermark_time is not None:
            start = mark.watermark_time.date() + timedelta(days=1)
        else:
            configured = self._start_dates.get(spec.job_id)
            if configured is None:
                return []  # 无水位且未配置起点：不自动触发（防历史全量拉取）
            start = configured
        if start > last_closed:
            return []
        return [(start, last_closed)]
