import pytest

from fin_data_hub import SecCode, Source, UnknownSecurityError
from fin_data_hub.mapping import get_mapper


@pytest.mark.parametrize("source", [Source.TUSHARE, Source.WIND, Source.IFIND])
def test_passthrough_sources(source: Source) -> None:
    mapper = get_mapper(source)
    code = SecCode.parse("600000.SH")
    assert mapper.to_source(code) == "600000.SH"
    assert mapper.from_source("600000.SH") == code


def test_get_mapper_accepts_plain_string() -> None:
    mapper = get_mapper("akshare")
    assert mapper.to_source(SecCode.parse("600000.SH")) == "600000"


def test_akshare_bare_codes_for_non_index() -> None:
    mapper = get_mapper(Source.AKSHARE)
    assert mapper.to_source(SecCode.parse("600000.SH")) == "600000"
    assert mapper.to_source(SecCode.parse("510300.SH")) == "510300"
    assert mapper.to_source(SecCode.parse("000001.OF")) == "000001"


def test_akshare_index_plain_vs_prefixed_endpoint() -> None:
    mapper = get_mapper(Source.AKSHARE)
    index = SecCode.parse("000300.SH")
    assert mapper.to_source(index, "index_zh_a_hist") == "000300"
    assert mapper.to_source(index, "stock_zh_index_daily_em") == "sh000300"
    assert (
        mapper.to_source(SecCode.parse("399006.SZ"), "stock_zh_index_daily_em")
        == "sz399006"
    )


def test_akshare_from_source_roundtrip() -> None:
    mapper = get_mapper(Source.AKSHARE)
    assert mapper.from_source("sh000300").canonical == "000300.SH"
    assert mapper.from_source("sz399006").canonical == "399006.SZ"
    assert mapper.from_source("600000", venue="SH").canonical == "600000.SH"


def test_akshare_from_source_requires_venue_for_bare_code() -> None:
    mapper = get_mapper(Source.AKSHARE)
    with pytest.raises(UnknownSecurityError):
        mapper.from_source("600000")


@pytest.mark.parametrize("source", [Source.TUSHARE, Source.WIND, Source.IFIND])
def test_passthrough_covers_hk_us_and_indices(source: Source) -> None:
    mapper = get_mapper(source)
    for text in ("00700.HK", "AAPL.O", "SPX.GI", "885800.TI", "881155.WI"):
        code = SecCode.parse(text, sec_type="stock" if text.endswith(".HK") else None)
        assert mapper.to_source(code) == text


def test_akshare_rejects_non_cn_venues() -> None:
    from fin_data_hub.errors import UnsupportedCapability

    mapper = get_mapper(Source.AKSHARE)
    with pytest.raises(UnsupportedCapability):
        mapper.to_source(SecCode.parse("AAPL.O"))
    with pytest.raises(UnsupportedCapability):
        mapper.to_source(SecCode.parse("SPX.GI"))
    with pytest.raises(UnsupportedCapability):
        mapper.to_source(SecCode.parse("00700.HK", sec_type="stock"))
