"""数据源适配器抽象。"""

from __future__ import annotations

from abc import ABC
from collections.abc import Sequence
from typing import ClassVar

import pandas as pd

from fin_data_hub.codes import SecCode
from fin_data_hub.enums import Source
from fin_data_hub.ratelimit import RateLimiterSet
from fin_data_hub.usage import UsageLedger


class BaseAdapter(ABC):
    """数据源适配器基类。

    ``capabilities`` 声明本适配器支持的端点能力；门面据此提前拒绝并给出
    可用 source 列表。具体取数方法返回**统一 schema** 的 DataFrame（尚未
    写入 attrs，由门面 :func:`fin_data_hub.schemas.finalize_frame` 完成）。
    """

    source: ClassVar[Source]
    capabilities: ClassVar[frozenset[str]] = frozenset()

    _usage: UsageLedger | None = None
    _rate_limits: RateLimiterSet | None = None

    def bind_rate_limits(self, limiter: RateLimiterSet) -> None:
        """由门面注入限流器；适配器在真实调用前 acquire。"""
        self._rate_limits = limiter

    def _acquire(self, endpoint: str) -> None:
        limiter = getattr(self, "_rate_limits", None)
        if limiter is not None:
            limiter.acquire(endpoint)

    # 能力名常量，供 facade 与测试引用
    CAP_BARS = "bars"
    CAP_SNAPSHOT = "snapshot"
    CAP_FUND_NAV = "fund_nav"
    CAP_REFERENCE = "reference"
    CAP_TRADE_CALENDAR = "trade_calendar"
    CAP_ADJUST_FACTORS = "adjust_factors"

    def bind_usage(self, ledger: UsageLedger) -> None:
        """由门面注入调用台账；适配器在真实调用边界记录。"""
        self._usage = ledger

    def _record(
        self,
        endpoint: str,
        *,
        calls: int = 1,
        codes: Sequence[str] = (),
        latency_ms: float = 0.0,
    ) -> None:
        ledger = getattr(self, "_usage", None)
        if ledger is not None:
            ledger.record(
                str(self.source),
                endpoint,
                calls=calls,
                codes=tuple(codes),
                latency_ms=latency_ms,
            )

    def fetch_bars(
        self,
        codes: list[SecCode],
        *,
        start: str,
        end: str,
        freq: str,
        adjust: str | None,
        fields: tuple[str, ...] | None,
    ) -> pd.DataFrame:  # pragma: no cover - 抽象方法
        raise NotImplementedError

    def fetch_snapshot(
        self,
        codes: list[SecCode],
        *,
        fields: tuple[str, ...] | None,
    ) -> pd.DataFrame:  # pragma: no cover - 抽象方法
        raise NotImplementedError

    def fetch_fund_nav(
        self,
        codes: list[SecCode],
        *,
        start: str | None,
        end: str | None,
    ) -> pd.DataFrame:  # pragma: no cover - 抽象方法
        raise NotImplementedError

    def fetch_reference(self, kind: str) -> pd.DataFrame:  # pragma: no cover
        raise NotImplementedError

    def fetch_trade_calendar(self, *, start: str, end: str) -> pd.DataFrame:
        raise NotImplementedError  # pragma: no cover

    def fetch_adjust_factors(
        self, codes: list[SecCode], *, start: str, end: str
    ) -> pd.DataFrame:  # pragma: no cover - 抽象方法
        raise NotImplementedError
