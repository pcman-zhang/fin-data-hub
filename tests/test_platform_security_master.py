"""Security Master（TASK-3.14 / doc-10 §3.3）测试：别名、as-of 宇宙、SCD2、Hub 构建。"""

from __future__ import annotations

import pandas as pd
import pytest

from fin_data_platform.security_master import SecurityMaster
from fin_data_platform.security_master.schema import TABLES


def _hub() -> SecurityMaster:
    sm = SecurityMaster()
    sm.register(
        canonical_code="600519.SH",
        sec_type="stock",
        name="贵州茅台",
        list_date="2001-08-27",
    )
    sm.register(
        canonical_code="000004.SZ",
        sec_type="stock",
        name="国华退",
        list_date="1991-01-14",
        delist_date="2026-07-14",
        status="D",
    )
    sm.register(
        canonical_code="000300.SH",
        sec_type="index",
        name="沪深300",
        list_date="2005-04-08",
    )
    return sm


def test_multi_source_alias_resolution() -> None:
    sm = _hub()
    sid = sm.resolve("canonical", "600519.SH")
    assert sid is not None
    assert sm.resolve("tushare", "600519.SH") == sid
    assert sm.resolve("baostock", "sh.600519") == sid
    assert sm.resolve("akshare", "600519") == sid
    assert sm.resolve("baostock", "sh.999999") is None


def test_alias_validity_window() -> None:
    sm = _hub()
    assert sm.resolve("canonical", "600519.SH", as_of="2000-01-01") is None
    assert sm.resolve("canonical", "600519.SH", as_of="2001-08-27") is not None


def test_universe_includes_delisted_until_delist_date() -> None:
    sm = _hub()
    codes_2019 = {item.canonical_code for item in sm.universe("2019-01-01")}
    assert codes_2019 == {"600519.SH", "000004.SZ", "000300.SH"}
    # delist_date 为不含端点（as_of < delist_date）
    codes_before = {item.canonical_code for item in sm.universe("2026-07-13")}
    assert "000004.SZ" in codes_before
    codes_after = {item.canonical_code for item in sm.universe("2026-07-14")}
    assert "000004.SZ" not in codes_after
    only_stock = {item.canonical_code for item in sm.universe("2019-01-01", sec_types=("stock",))}
    assert only_stock == {"600519.SH", "000004.SZ"}


def test_name_and_status_as_of_scd2() -> None:
    sm = _hub()
    sid = sm.resolve("canonical", "600519.SH")
    assert sid is not None
    sm.add_attribute(
        sid, attribute="name", value="G茅台", start_date="2006-05-25", end_date="2006-10-08"
    )
    sm.add_attribute(sid, attribute="name", value="贵州茅台", start_date="2006-10-09")
    sm.add_status(sid, status="L", start_date="2001-08-27", end_date="2020-05-31")
    sm.add_status(sid, status="D", start_date="2020-06-01")
    assert sm.name_as_of(sid, "2006-06-01") == "G茅台"
    assert sm.name_as_of(sid, "2007-01-01") == "贵州茅台"
    # 有区间但目标日未被覆盖 → None（防前视，不回退当前值）
    assert sm.name_as_of(sid, "1990-01-01") is None
    assert sm.status_as_of(sid, "2019-01-01") == "L"
    assert sm.status_as_of(sid, "2021-01-01") == "D"
    assert sm.status_as_of(sid, "1990-01-01") is None


class FakeHub:
    def __init__(self) -> None:
        self._frames = {
            "stock_list": pd.DataFrame(
                [
                    {
                        "code": "600519.SH",
                        "name": "贵州茅台",
                        "list_date": "2001-08-27",
                        "market": "SH",
                        "list_status": "L",
                    },
                    {
                        "code": "000001.SZ",
                        "name": "平安银行",
                        "list_date": "1991-04-03",
                        "market": "SZ",
                        "list_status": "L",
                    },
                ]
            ),
            "etf_list": pd.DataFrame(
                [
                    {
                        "code": "510300.SH",
                        "name": "300ETF",
                        "list_date": "2012-05-28",
                        "list_status": "L",
                    }
                ]
            ),
            "fund_list": pd.DataFrame(
                [
                    {
                        "code": "510300.SH",
                        "name": "300ETF",
                        "list_date": "2012-05-28",
                        "list_status": "L",
                    },
                    {
                        "code": "000001.OF",
                        "name": "华夏成长",
                        "list_date": pd.NaT,
                        "list_status": "L",
                    },
                ]
            ),
            "index_list": pd.DataFrame(
                [
                    {"code": "000300.SH", "name": "沪深300", "list_date": "2005-04-08"},
                    {"code": float("nan"), "name": "坏行", "list_date": None},
                ]
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
    sm = SecurityMaster()
    stats = sm.build_from_hub(
        FakeHub(), namechange_start="2000-01-01", namechange_end="2026-12-31"
    )
    # 2 股票 + 1 ETF + 1 场外基金 + 1 指数 + 1 退市（NaN 行跳过）
    assert stats.registered == 6
    assert stats.attributes == 1
    assert stats.aliases >= stats.registered  # 每个新标的至少 canonical 别名
    sid = sm.resolve("canonical", "600519.SH")
    assert sid is not None
    assert sm.name_as_of(sid, "2006-06-01") == "G茅台"
    assert sm.resolve("baostock", "sh.600519") == sid
    # ETF 先于基金列表注册：类型不被泛化为 fund
    etf = sm.resolve("canonical", "510300.SH")
    assert etf is not None
    etf_record = sm.security(etf)
    assert etf_record is not None and etf_record.sec_type == "etf"
    # NaT 上市日不打断宇宙查询
    assert {item.canonical_code for item in sm.universe("2020-01-01")} >= {
        "600519.SH",
        "000001.OF",
    }
    # 退市标的的 SCD2 状态历史
    delisted = sm.resolve("canonical", "000004.SZ")
    assert delisted is not None
    assert sm.status_as_of(delisted, "2010-01-01") == "L"
    assert sm.status_as_of(delisted, "2027-01-01") == "D"


def test_incremental_delist_refresh() -> None:
    """首日以 L 注册，次日从 stock_list 消失并进入 delist_list → 刷新为 D 并从宇宙移除。"""

    class DelistHub(FakeHub):
        def __init__(self, delisted: bool) -> None:
            super().__init__()
            listed_row = pd.DataFrame(
                [
                    {
                        "code": "000004.SZ",
                        "name": "国华退",
                        "list_date": "1991-01-14",
                        "market": "SZ",
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

    sm = SecurityMaster()
    sm.build_from_hub(DelistHub(delisted=False))
    assert "000004.SZ" in {item.canonical_code for item in sm.universe("2026-09-10")}

    stats = sm.build_from_hub(DelistHub(delisted=True))
    assert stats.updated == 1
    assert {item.canonical_code for item in sm.universe("2026-09-10")} == {
        "600519.SH",
        "000001.SZ",
        "510300.SH",
        "000001.OF",
        "000300.SH",
    }
    sid = sm.resolve("canonical", "000004.SZ")
    assert sid is not None
    assert sm.status_as_of(sid, "2020-01-01") == "L"
    assert sm.status_as_of(sid, "2027-01-01") == "D"


def test_schema_tables_defined() -> None:
    names = {table.key for table in TABLES}
    assert names == {
        "ref.security_master",
        "ref.security_alias",
        "ref.security_status_history",
        "ref.security_attribute_history",
    }
    pk = {column.name for column in TABLES[0].primary_key}
    assert pk == {"security_id", "valid_from"}


def test_universe_requires_as_of() -> None:
    with pytest.raises(ValueError, match="as_of"):
        _hub().universe(None)
