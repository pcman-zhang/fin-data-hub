"""交易日历适配（TASK-3.6 切片 2）：由 FinDataHub 日历推导「最近已收盘交易日」。

知识时间口径：A 股 15:00 收盘 = 07:00 UTC；但**调度判定**需等源端发布
（15:00–16:00 CST），故默认以 16:30 CST（08:30 UTC）为「今日已收盘」截止，
避免在发布前取到空数据并错误推进水位。
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, time, timedelta
from typing import Any, Protocol

from fin_data_platform.registry._util import to_date
from fin_data_platform.runtime._util import utcnow

#: 调度判定「今日已收盘」的截止（16:30 CST = 08:30 UTC）
_PUBLISH_CUTOFF_UTC = time(8, 30)


class TradeCalendar(Protocol):
    """日历协议（测试与 Hub 实现可互换）。"""

    def is_trading_day(self, day: date) -> bool: ...

    def last_closed(self, now: datetime) -> date | None: ...


class HubTradeCalendar:
    """Hub 日历实现（进程内缓存；按需向前回溯窗口加载）。"""

    def __init__(
        self,
        hub: Any,
        *,
        source: Any = None,
        lookback_days: int = 45,
        publish_cutoff_utc: time = _PUBLISH_CUTOFF_UTC,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self._hub = hub
        self._source = source
        self._lookback = lookback_days
        self._publish_cutoff = publish_cutoff_utc
        self._clock = clock
        self._cache: dict[date, set[date]] = {}

    def _load(self, end: date) -> set[date]:
        """加载 ``[end-lookback, end]`` 的交易日集合（含缓存）。"""
        if end in self._cache:
            return self._cache[end]
        start = end - timedelta(days=self._lookback)
        frame = self._hub.get_trade_calendar(
            start=start.isoformat(), end=end.isoformat(), source=self._source
        )
        days: set[date] = set()
        if frame is not None and not frame.empty:
            for row in frame.to_dict("records"):
                day = to_date(row.get("date"))
                if day is not None and bool(row.get("is_open", True)):
                    days.add(day)
        self._cache[end] = days
        return days

    def is_trading_day(self, day: date) -> bool:
        return day in self._load(day)

    def last_closed(self, now: datetime | None = None) -> date | None:
        moment = now or self._clock()
        today = moment.date()
        closed_end = (
            today
            if moment.time() >= self._publish_cutoff
            else today - timedelta(days=1)
        )
        days = [day for day in self._load(closed_end) if day <= closed_end]
        return max(days) if days else None
