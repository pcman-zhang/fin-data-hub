"""端点能力元数据（驱动请求分块与合并）。

表键：``(Source, capability)``；capability 与 :class:`~fin_data_hub.sources.base.BaseAdapter`
的 ``CAP_*`` 常量一致，另含适配器级能力（如 ``"edb"``）。

约定：
- ``max_codes_per_call=None`` 表示单次调用可容纳任意多代码（由适配器内部处理）；
- ``max_indicators_per_call=None`` 表示不限，``1`` 表示一次仅一个指标；
- ``cost_class`` 为通用成本分级（``free`` / ``metered`` / ``premium``），
  不包含任何厂商具体价格。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from fin_data_hub.codes import SecCode
from fin_data_hub.enums import Source

CostClass = Literal["free", "metered", "premium"]


@dataclass(frozen=True, slots=True)
class EndpointCapability:
    max_codes_per_call: int | None = None
    max_indicators_per_call: int | None = None
    supports_multi_symbol: bool = True
    supports_history: bool = True
    cost_class: CostClass = "free"


_DEFAULT = EndpointCapability()

CAPABILITIES: dict[tuple[Source, str], EndpointCapability] = {
    # Tushare：ts_code 支持逗号批量；限额随积分档变化，由限流器/预算配置控制
    (Source.TUSHARE, "bars"): EndpointCapability(
        max_codes_per_call=None, cost_class="free"
    ),
    (Source.TUSHARE, "fund_nav"): EndpointCapability(
        max_codes_per_call=None, cost_class="free"
    ),
    (Source.TUSHARE, "adjust_factors"): EndpointCapability(
        max_codes_per_call=None, cost_class="free"
    ),
    # AkShare：各接口均为单标的形式
    (Source.AKSHARE, "bars"): EndpointCapability(
        max_codes_per_call=1, supports_multi_symbol=False, cost_class="free"
    ),
    (Source.AKSHARE, "snapshot"): EndpointCapability(
        max_codes_per_call=1, supports_multi_symbol=False, cost_class="free"
    ),
    (Source.AKSHARE, "fund_nav"): EndpointCapability(
        max_codes_per_call=1, supports_multi_symbol=False, cost_class="free"
    ),
    # iFinD：NL 工具普遍支持多标的/多指标聚合（已抽验 stock/fund/edb）；
    # max_codes_per_call=50 是请求体积的安全上限，非接口限制
    (Source.IFIND, "bars"): EndpointCapability(
        max_codes_per_call=50, supports_multi_symbol=True, cost_class="metered"
    ),
    (Source.IFIND, "fund_nav"): EndpointCapability(
        max_codes_per_call=50, supports_multi_symbol=True, cost_class="metered"
    ),
    (Source.IFIND, "edb"): EndpointCapability(
        max_indicators_per_call=None, supports_multi_symbol=True, cost_class="metered"
    ),
    # Fuyao：K 线单标的且窗口 ≤10 年；快照支持 thscodes 批量（50 为安全上限）
    (Source.FUYAO, "bars"): EndpointCapability(
        max_codes_per_call=1, supports_multi_symbol=False, cost_class="free"
    ),
    (Source.FUYAO, "snapshot"): EndpointCapability(
        max_codes_per_call=50, cost_class="free"
    ),
    # Wind：K 线单代码；快照单次 ≤50；EDB 精确代码可批量
    (Source.WIND, "bars"): EndpointCapability(
        max_codes_per_call=1, supports_multi_symbol=False, cost_class="premium"
    ),
    (Source.WIND, "snapshot"): EndpointCapability(
        max_codes_per_call=50, cost_class="premium"
    ),
    (Source.WIND, "edb"): EndpointCapability(
        max_indicators_per_call=None, cost_class="premium"
    ),
}


def get_capability(source: Source | str, capability: str) -> EndpointCapability:
    """返回能力元数据；未登记的组合返回默认值（不限代码数）。"""
    return CAPABILITIES.get((Source(source), capability), _DEFAULT)


def split_codes(
    source: Source | str,
    capability: str,
    codes: list[SecCode],
) -> list[list[SecCode]]:
    """按能力上限把代码列表切成多个调用批次（保持原顺序）。"""
    limit = get_capability(source, capability).max_codes_per_call
    if limit is None or len(codes) <= limit:
        return [list(codes)]
    return [codes[index : index + limit] for index in range(0, len(codes), limit)]
