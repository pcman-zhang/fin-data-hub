"""数据源适配器抽象。"""

from __future__ import annotations

from abc import ABC
from typing import ClassVar

import pandas as pd

from fin_data_hub.codes import SecCode
from fin_data_hub.enums import Source


class BaseAdapter(ABC):
    """数据源适配器基类。

    ``capabilities`` 声明本适配器支持的端点能力；门面据此提前拒绝并给出
    可用 source 列表。具体取数方法返回**统一 schema** 的 DataFrame（尚未
    写入 attrs，由门面 :func:`fin_data_hub.schemas.finalize_frame` 完成）。
    """

    source: ClassVar[Source]
    capabilities: ClassVar[frozenset[str]] = frozenset()

    # 能力名常量，供 facade 与测试引用
    CAP_BARS = "bars"
    CAP_SNAPSHOT = "snapshot"
    CAP_FUND_NAV = "fund_nav"
    CAP_REFERENCE = "reference"
    CAP_TRADE_CALENDAR = "trade_calendar"

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
