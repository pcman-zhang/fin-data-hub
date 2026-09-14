"""引用注册表（doc-10 §3.3）测试：身份/代码履历、as-of 宇宙、SCD2、Hub 构建。"""

from __future__ import annotations

import pandas as pd
import pytest

from fin_data_platform.registry import EntityRegistry
from fin_data_platform.registry.schema import TABLES


def _registry() -> EntityRegistry:
    registry = EntityRegistry()
    registry.register(
        code="600519.SH",
        name="贵州茅台",
        sec_type="stock",
        list_date="2001-08-27",
    )
    registry.register(
        code="000004.SZ",
        name="国华退",
        sec_type="stock",
        list_date="1991-01-14",
        delist_date="2026-07-14",
        status="D",
    )
    registry.register(
        code="000300.SH",
        name="沪深300",
        sec_type="index",
        list_date="2005-04-08",
    )
    return registry


def test_register_and_resolve() -> None:
    registry = _registry()
    entity_id = registry.resolve("600519.SH")
    assert entity_id is not None
    assert registry.resolve("000300.SH") is not None
    assert registry.resolve("600000.SH") is None


def test_code_history_resolution() -> None:
    registry = _registry()
    entity_id = registry.resolve("600519.SH")
    assert entity_id is not None
    registry.add_code_change(entity_id, new_code="920519.BJ", start_date="2026-01-01")
    # 新代码可解析
    assert registry.resolve("920519.BJ") == entity_id
    # 旧代码在变更前有效、变更后失效
    assert registry.resolve("600519.SH", as_of="2025-12-31") == entity_id
    assert registry.resolve("600519.SH", as_of="2026-06-01") is None
    # 当前属性行代码已更新
    current = registry.entity(entity_id)
    assert current is not None and current.code == "920519.BJ"


def test_universe_includes_delisted_until_delist_date() -> None:
    registry = _registry()
    codes_2019 = {item.code for item in registry.universe("2019-01-01")}
    assert codes_2019 == {"600519.SH", "000004.SZ", "000300.SH"}
    assert "000004.SZ" in {item.code for item in registry.universe("2026-07-13")}
    assert "000004.SZ" not in {item.code for item in registry.universe("2026-07-14")}
    only_stock = {
        item.code for item in registry.universe("2019-01-01", sec_type="stock")
    }
    assert only_stock == {"600519.SH", "000004.SZ"}


def test_register_name_refresh_applies() -> None:
    registry = EntityRegistry()
    registry.register(
        code="600519.SH", name="贵州茅台", sec_type="stock", list_date="2001-08-27"
    )
    registry.register(code="600519.SH", name="茅台股份", sec_type="stock")
    entity_id = registry.resolve("600519.SH")
    assert entity_id is not None
    current = registry.entity(entity_id)
    assert current is not None and current.name == "茅台股份"
    assert registry.name_as_of(entity_id, "2025-01-01") == "茅台股份"


def test_entity_current_excludes_expired_temporary_name() -> None:
    registry = _registry()
    entity_id = registry.resolve("600519.SH")
    assert entity_id is not None
    registry.add_name_change(
        entity_id, name="ST茅台", start_date="2010-01-01", end_date="2011-12-31"
    )
    current = registry.entity(entity_id)
    assert current is not None and current.name == "贵州茅台"  # 当前行非临时行
    assert registry.name_as_of(entity_id, "2010-06-01") == "ST茅台"
    assert registry.name_as_of(entity_id, "2013-06-01") == "贵州茅台"  # 恢复行


def test_delist_applies_new_name() -> None:
    registry = EntityRegistry()
    registry.register(
        code="000004.SZ", name="国华", sec_type="stock", list_date="1991-01-14"
    )
    registry.register(
        code="000004.SZ", name="国华退", delist_date="2026-07-14", status="D"
    )
    entity_id = registry.resolve("000004.SZ")
    assert entity_id is not None
    assert registry.name_as_of(entity_id, "2027-01-01") == "国华退"


def test_name_and_status_as_of_scd2() -> None:
    registry = _registry()
    entity_id = registry.resolve("600519.SH")
    assert entity_id is not None
    registry.add_name_change(
        entity_id, name="G茅台", start_date="2006-05-25", end_date="2006-10-08"
    )
    assert registry.name_as_of(entity_id, "2006-06-01") == "G茅台"
    # 名称区间结束后回到后续行名称
    assert registry.name_as_of(entity_id, "2007-01-01") == "贵州茅台"
    # 早于全部行 → None（防前视）
    assert registry.name_as_of(entity_id, "1990-01-01") is None
    assert registry.status_as_of(entity_id, "2019-01-01") == "L"
    delisted_id = registry.resolve("000004.SZ")
    assert delisted_id is not None
    assert registry.status_as_of(delisted_id, "2020-01-01") == "L"
    assert registry.status_as_of(delisted_id, "2027-01-01") == "D"


class FakeHub:
    def __init__(self) -> None:
        self._frames = {
            "stock_list": pd.DataFrame(
                [
                    {
                        "code": "600519.SH",
                        "name": "贵州茅台",
                        "list_date": "2001-08-27",
                        "list_status": "L",
                    },
                    {
                        "code": "000001.SZ",
                        "name": "平安银行",
                        "list_date": "1991-04-03",
                        "list_status": "L",
                    },
                ]
            ),
            "etf_list": pd.DataFrame(
                [{"code": "510300.SH", "name": "300ETF", "list_date": "2012-05-28"}]
            ),
            "fund_list": pd.DataFrame(
                [
                    {"code": "510300.SH", "name": "300ETF", "list_date": "2012-05-28"},
                    {"code": "000001.OF", "name": "华夏成长", "list_date": pd.NaT},
                ]
            ),
            "index_list": pd.DataFrame(
                [{"code": "000300.SH", "name": "沪深300", "list_date": "2005-04-08"}]
            ),
            "delist_list": pd.DataFrame(
                [
                    {
                        "code": "000004.SZ",
                        "name": "国华退",
                        "list_date": "1991-01-14",
                        "delist_date": "2026-07-14",
                    }
                ]
            ),
        }
        self._events = {
            "namechange": pd.DataFrame(
                [
                    {
                        "code": "600519.SH",
                        "name": "G茅台",
                        "start_date": "2006-05-25",
                        "end_date": "2006-10-08",
                        "ann_date": "2006-05-22",
                    }
                ]
            )
        }

    def get_reference(self, kind: str) -> pd.DataFrame:
        if kind not in self._frames:
            raise ValueError(kind)
        return self._frames[kind]

    def get_market_events(self, *, kind: str, start: str, end: str) -> pd.DataFrame:
        if kind not in self._events:
            raise ValueError(kind)
        return self._events[kind]


def test_build_from_hub() -> None:
    registry = EntityRegistry()
    stats = registry.build_from_hub(
        FakeHub(), namechange_start="2000-01-01", namechange_end="2026-12-31"
    )
    assert stats.registered == 6  # 2 股票 + 1 ETF + 1 场外基金 + 1 指数 + 1 退市
    assert stats.attributes == 1
    entity_id = registry.resolve("600519.SH")
    assert entity_id is not None
    assert registry.name_as_of(entity_id, "2006-06-01") == "G茅台"
    etf_id = registry.resolve("510300.SH")
    assert etf_id is not None
    etf = registry.entity(etf_id)
    assert etf is not None and etf.sec_type == "etf"


def test_incremental_delist_refresh() -> None:
    class DelistHub(FakeHub):
        def __init__(self, delisted: bool) -> None:
            super().__init__()
            listed_row = pd.DataFrame(
                [
                    {
                        "code": "000004.SZ",
                        "name": "国华退",
                        "list_date": "1991-01-14",
                        "list_status": "L",
                    }
                ]
            )
            if delisted:
                stocks = self._frames["stock_list"]
                self._frames["stock_list"] = stocks[
                    stocks["code"] != "000004.SZ"
                ].reset_index(drop=True)
            else:
                self._frames["stock_list"] = pd.concat(
                    [self._frames["stock_list"], listed_row], ignore_index=True
                )
                self._frames["delist_list"] = pd.DataFrame(
                    columns=["code", "name", "list_date", "delist_date"]
                )

    registry = EntityRegistry()
    registry.build_from_hub(DelistHub(delisted=False))
    assert "000004.SZ" in {item.code for item in registry.universe("2026-09-10")}
    stats = registry.build_from_hub(DelistHub(delisted=True))
    assert stats.updated == 1
    assert {item.code for item in registry.universe("2026-09-10")} == {
        "600519.SH",
        "000001.SZ",
        "510300.SH",
        "000001.OF",
        "000300.SH",
    }
    entity_id = registry.resolve("000004.SZ")
    assert entity_id is not None
    assert registry.status_as_of(entity_id, "2020-01-01") == "L"
    assert registry.status_as_of(entity_id, "2027-01-01") == "D"


def test_schema_tables_defined() -> None:
    names = {table.key for table in TABLES}
    assert names == {"ref.entity", "ref.entity_code_history"}
    pk = {column.name for column in TABLES[0].primary_key}
    assert pk == {"entity_id", "valid_from", "knowledge_time", "version"}
    code_pk = {column.name for column in TABLES[1].primary_key}
    assert code_pk == {"entity_id", "code", "valid_from", "knowledge_time", "version"}


def test_universe_requires_as_of() -> None:
    with pytest.raises(ValueError, match="as_of"):
        _registry().universe(None)
