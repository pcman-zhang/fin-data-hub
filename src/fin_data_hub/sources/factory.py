"""适配器工厂：按配置最佳努力构建注册表。

规则：
- 仅当对应配置子对象与凭证存在时才注册该源；
- 依赖缺失（SDK / httpx 未安装）时跳过并记录 warning，不阻塞其他源；
- AkShare 无凭证，尝试导入成功即注册。
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable

from fin_data_hub.config import HubConfig
from fin_data_hub.enums import Source
from fin_data_hub.errors import FinDataHubError
from fin_data_hub.sources.base import BaseAdapter
from fin_data_hub.sources.registry import SourceRegistry

logger = logging.getLogger("fin_data_hub.factory")


def build_registry(
    config: HubConfig | None = None,
    *,
    sources: Iterable[Source | str] | None = None,
) -> SourceRegistry:
    """按配置构建 ``SourceRegistry``（缺凭证/依赖的源跳过）。"""
    cfg = config or HubConfig()
    requested = {Source(item) for item in sources} if sources is not None else None

    def wants(source: Source) -> bool:
        return requested is None or source in requested

    registry = SourceRegistry()

    if wants(Source.TUSHARE) and cfg.tushare and cfg.tushare.token:
        _try_register(
            registry,
            "tushare",
            lambda: _tushare_adapter(cfg),
        )
    if wants(Source.WIND) and cfg.wind and cfg.wind.api_key:
        _try_register(registry, "wind", lambda: _wind_adapter(cfg))
    if wants(Source.IFIND) and cfg.ifind and cfg.ifind.authorization:
        _try_register(registry, "ifind", lambda: _ifind_adapter(cfg))
    if wants(Source.AKSHARE):
        _try_register(registry, "akshare", _akshare_adapter)
    return registry


def _try_register(
    registry: SourceRegistry, name: str, factory: Callable[[], BaseAdapter]
) -> None:
    try:
        registry.register(factory())
    except (FinDataHubError, ImportError) as exc:
        logger.warning("跳过 %s 适配器：%s", name, exc)


def _tushare_adapter(config: HubConfig) -> BaseAdapter:
    from fin_data_hub.sources.tushare import TushareAdapter

    return TushareAdapter(config.tushare)


def _wind_adapter(config: HubConfig) -> BaseAdapter:
    from fin_data_hub.sources.wind import WindAdapter

    return WindAdapter(config.wind)


def _ifind_adapter(config: HubConfig) -> BaseAdapter:
    from fin_data_hub.sources.ifind import IfindAdapter

    return IfindAdapter(config.ifind)


def _akshare_adapter() -> BaseAdapter:
    from fin_data_hub.sources.akshare import AkShareAdapter

    return AkShareAdapter()
