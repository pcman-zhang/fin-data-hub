"""真实数据源端到端测试（默认跳过）。

运行方式：``pytest -m integration``，并按需配置环境变量：

- Tushare：``FIN_DATA_HUB_TUSHARE_TOKEN``
- Wind：``FIN_DATA_HUB_WIND_API_KEY``
- 同花顺 iFinD：``FIN_DATA_HUB_IFIND_TOKEN``
- AkShare：无需凭证（需外网）

凭证缺失或依赖包未安装时对应测试自动 skip。
"""

import importlib.util
import os

import pytest

from fin_data_hub import (
    FinDataHub,
    FuyaoConfig,
    HubConfig,
    IfindConfig,
    Source,
    TushareConfig,
    WindConfig,
)
from fin_data_hub.sources.akshare import AkShareAdapter
from fin_data_hub.sources.fuyao import FuyaoAdapter
from fin_data_hub.sources.ifind import IfindAdapter
from fin_data_hub.sources.registry import SourceRegistry
from fin_data_hub.sources.tushare import TushareAdapter
from fin_data_hub.sources.wind import WindAdapter

pytestmark = pytest.mark.integration

TUSHARE_TOKEN = os.environ.get("FIN_DATA_HUB_TUSHARE_TOKEN")
WIND_API_KEY = os.environ.get("FIN_DATA_HUB_WIND_API_KEY")
IFIND_TOKEN = os.environ.get("FIN_DATA_HUB_IFIND_TOKEN")
FUYAO_API_KEY = os.environ.get("FIN_DATA_HUB_FUYAO_API_KEY")


def _installed(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


@pytest.mark.skipif(
    not (TUSHARE_TOKEN and _installed("tushare")),
    reason="需要 FIN_DATA_HUB_TUSHARE_TOKEN 与 tushare 包",
)
def test_tushare_live_bars() -> None:
    config = HubConfig(tushare=TushareConfig(token=TUSHARE_TOKEN))
    hub = FinDataHub(config, registry=SourceRegistry([TushareAdapter(config.tushare)]))
    df = hub.get_bars(
        ["600000.SH"], start="2026-09-01", end="2026-09-11", source=Source.TUSHARE
    )
    assert not df.empty
    assert df.attrs["source"] == "tushare"
    assert {"code", "date", "open", "close", "volume", "amount"} <= set(df.columns)


@pytest.mark.skipif(not _installed("akshare"), reason="需要 akshare 包与外网")
def test_akshare_live_bars() -> None:
    hub = FinDataHub(HubConfig(), registry=SourceRegistry([AkShareAdapter()]))
    df = hub.get_bars(
        ["600000.SH"], start="2026-09-01", end="2026-09-11", source=Source.AKSHARE
    )
    assert not df.empty
    assert df.attrs["source"] == "akshare"


@pytest.mark.skipif(not WIND_API_KEY, reason="需要 FIN_DATA_HUB_WIND_API_KEY")
def test_wind_live_bars() -> None:
    config = HubConfig(wind=WindConfig(api_key=WIND_API_KEY))
    hub = FinDataHub(config, registry=SourceRegistry([WindAdapter(config.wind)]))
    df = hub.get_bars(
        ["600519.SH"], start="2026-09-09", end="2026-09-11", source=Source.WIND
    )
    assert not df.empty
    assert df.attrs["source"] == "wind"


@pytest.mark.skipif(not IFIND_TOKEN, reason="需要 FIN_DATA_HUB_IFIND_TOKEN")
def test_ifind_live_index_bars() -> None:
    config = HubConfig(ifind=IfindConfig(authorization=IFIND_TOKEN))
    hub = FinDataHub(config, registry=SourceRegistry([IfindAdapter(config.ifind)]))
    df = hub.get_bars(
        ["000300.SH"], start="2026-09-01", end="2026-09-11", source=Source.IFIND
    )
    assert not df.empty
    assert df.attrs["source"] == "ifind"


@pytest.mark.skipif(not FUYAO_API_KEY, reason="需要 FIN_DATA_HUB_FUYAO_API_KEY")
def test_fuyao_live_snapshot_and_bars() -> None:
    config = HubConfig(fuyao=FuyaoConfig(api_key=FUYAO_API_KEY))
    hub = FinDataHub(config, registry=SourceRegistry([FuyaoAdapter(config.fuyao)]))
    snapshot = hub.get_snapshot(["600519.SH"], source=Source.FUYAO)
    assert not snapshot.empty
    assert snapshot.attrs["source"] == "fuyao"
    bars = hub.get_bars(
        ["600519.SH"], start="2026-09-01", end="2026-09-11", source=Source.FUYAO
    )
    assert not bars.empty
