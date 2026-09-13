import pandas as pd
import pytest

from fin_data_hub import Capability, Source
from fin_data_hub.errors import ResponseParseError
from fin_data_hub.specs import load_all_specs, load_spec, normalize, validate_specs

COVERAGE: dict[Source, set[Capability]] = {
    Source.TUSHARE: {
        Capability.BARS,
        Capability.FUND_NAV,
        Capability.TRADE_CALENDAR,
        Capability.ADJUST_FACTORS,
    },
    Source.AKSHARE: {
        Capability.BARS,
        Capability.FUND_NAV,
        Capability.TRADE_CALENDAR,
    },
    Source.WIND: {Capability.BARS, Capability.SNAPSHOT},
    Source.FUYAO: {
        Capability.BARS,
        Capability.SNAPSHOT,
        Capability.ADJUSTMENT_EVENTS,
        Capability.TRADE_CALENDAR,
    },
}


def test_specs_are_structurally_valid() -> None:
    assert validate_specs() == []


def test_spec_coverage() -> None:
    specs = load_all_specs()
    for source, endpoints in COVERAGE.items():
        assert source in specs, f"缺少 {source} spec"
        for endpoint in endpoints:
            assert endpoint.value in specs[source].responses, (
                f"{source} 缺少 {endpoint} 映射"
            )


def test_normalize_tushare_bars_units_and_dates() -> None:
    spec = load_spec(Source.TUSHARE).responses["bars"]
    raw = pd.DataFrame(
        {
            "ts_code": ["600000.SH"],
            "trade_date": ["20260105"],
            "open": [10.0],
            "high": [10.5],
            "low": [9.9],
            "close": [10.3],
            "vol": [1000.0],
            "amount": [1030.0],
        }
    )
    frame = normalize(raw, spec, source=Source.TUSHARE)
    assert frame["code"].tolist() == ["600000.SH"]
    assert str(frame["date"].dtype) == "datetime64[ns]"
    assert frame["volume"].tolist() == [100_000.0]  # 手 → 股
    assert frame["amount"].tolist() == [1_030_000.0]  # 千元 → 元


def test_normalize_fuyao_snapshot_date_ms() -> None:
    spec = load_spec(Source.FUYAO).responses["snapshot"]
    ms = 1757558400000
    raw = pd.DataFrame(
        {
            "thscode": ["600519.SH"],
            "date_ms": [ms],
            "last_price": [1277.8],
            "open_price": [1252.08],
            "high_price": [1282.0],
            "low_price": [1250.21],
            "prev_price": [1256.0],
            "volume": [3_098_875],
            "turnover": [3_937_375_200.0],
        }
    )
    frame = normalize(raw, spec, source=Source.FUYAO)
    # 快照日期来自响应信封 timestamp（adapter 级处理），spec 不映射 date
    assert "date" not in frame.columns
    assert frame["last"].tolist() == [1277.8]
    assert frame["code"].tolist() == ["600519.SH"]


def test_normalize_missing_required_raises() -> None:
    spec = load_spec(Source.TUSHARE).responses["bars"]
    raw = pd.DataFrame({"ts_code": ["600000.SH"]})
    with pytest.raises(ResponseParseError, match="缺少字段"):
        normalize(raw, spec, source=Source.TUSHARE)


def test_normalize_missing_mapped_field_raises() -> None:
    from fin_data_hub.specs import FieldSpec, ResponseSpec

    spec = ResponseSpec(
        required=("a",), fields={"code": FieldSpec(source="missing", type="code")}
    )
    raw = pd.DataFrame({"a": [1]})
    with pytest.raises(ResponseParseError, match="缺少映射源字段"):
        normalize(raw, spec, source=Source.FUYAO)
