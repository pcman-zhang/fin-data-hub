import sys
import types

from fin_data_hub import DataHub, HubConfig, IfindConfig, Source, TushareConfig, WindConfig
from fin_data_hub.sources.factory import build_registry


def test_unconfigured_sources_are_skipped() -> None:
    registry = build_registry(
        HubConfig(), sources=[Source.TUSHARE, Source.WIND, Source.IFIND]
    )
    assert registry.available() == ()


def test_tushare_registered_with_fake_package(monkeypatch) -> None:
    fake = types.ModuleType("tushare")
    fake.pro_api = lambda token: types.SimpleNamespace()
    monkeypatch.setitem(sys.modules, "tushare", fake)

    registry = build_registry(
        HubConfig(tushare=TushareConfig(token="token")), sources=[Source.TUSHARE]
    )
    assert registry.available() == ("tushare",)


def test_tushare_missing_package_is_skipped(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "tushare", None)
    registry = build_registry(
        HubConfig(tushare=TushareConfig(token="token")), sources=[Source.TUSHARE]
    )
    assert registry.available() == ()


def test_wind_and_ifind_registered_with_credentials() -> None:
    wind = build_registry(
        HubConfig(wind=WindConfig(api_key="key")), sources=[Source.WIND]
    )
    assert wind.available() == ("wind",)

    ifind = build_registry(
        HubConfig(ifind=IfindConfig(authorization="token")), sources=[Source.IFIND]
    )
    assert ifind.available() == ("ifind",)


def test_akshare_registered_when_package_available(monkeypatch) -> None:
    fake = types.ModuleType("akshare")
    monkeypatch.setitem(sys.modules, "akshare", fake)
    registry = build_registry(HubConfig(), sources=[Source.AKSHARE])
    assert registry.available() == ("akshare",)


def test_datahub_from_config_wires_registry(monkeypatch) -> None:
    fake = types.ModuleType("tushare")
    fake.pro_api = lambda token: types.SimpleNamespace()
    monkeypatch.setitem(sys.modules, "tushare", fake)

    hub = DataHub.from_config(HubConfig(tushare=TushareConfig(token="token")))
    assert hub.registry.available() == ("tushare",)
