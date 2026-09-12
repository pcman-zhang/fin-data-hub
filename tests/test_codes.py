import pytest

from fin_data_hub import SecCode, SecType, UnknownSecurityError, parse_codes


@pytest.mark.parametrize(
    ("text", "symbol", "venue", "sec_type"),
    [
        ("600000.SH", "600000", "SH", SecType.STOCK),
        ("688001.SH", "688001", "SH", SecType.STOCK),
        ("510300.SH", "510300", "SH", SecType.ETF),
        ("501050.SH", "501050", "SH", SecType.LOF),
        ("000300.SH", "000300", "SH", SecType.INDEX),
        ("000001.SZ", "000001", "SZ", SecType.STOCK),
        ("300750.SZ", "300750", "SZ", SecType.STOCK),
        ("159915.SZ", "159915", "SZ", SecType.ETF),
        ("166009.SZ", "166009", "SZ", SecType.LOF),
        ("399006.SZ", "399006", "SZ", SecType.INDEX),
        ("920002.BJ", "920002", "BJ", SecType.STOCK),
        ("000001.OF", "000001", "OF", SecType.FUND),
    ],
)
def test_parse_and_infer(text: str, symbol: str, venue: str, sec_type: SecType) -> None:
    code = SecCode.parse(text)
    assert (code.symbol, code.venue, code.sec_type) == (symbol, venue, sec_type)
    assert str(code) == text


def test_lowercase_venue_and_zero_padding() -> None:
    code = SecCode.parse("1.sz")
    assert code.canonical == "000001.SZ"
    assert code.sec_type is SecType.STOCK


def test_bare_code_rejected() -> None:
    with pytest.raises(UnknownSecurityError):
        SecCode.parse("600000")


def test_unknown_venue_rejected() -> None:
    with pytest.raises(UnknownSecurityError):
        SecCode.parse("600000.XX")


def test_non_numeric_cn_symbol_rejected() -> None:
    with pytest.raises(UnknownSecurityError):
        SecCode.parse("ABCDEF.SH")


def test_ambiguity_between_sz_stock_and_of_fund() -> None:
    stock = SecCode.parse("000001.SZ")
    fund = SecCode.parse("000001.OF")
    assert stock != fund
    assert stock.canonical == "000001.SZ"
    assert fund.canonical == "000001.OF"
    assert stock.sec_type is SecType.STOCK
    assert fund.sec_type is SecType.FUND


def test_explicit_sec_type_overrides_inference() -> None:
    code = SecCode.parse("000300.SH", sec_type="etf")
    assert code.sec_type is SecType.ETF


def test_reserved_venue_requires_explicit_sec_type() -> None:
    with pytest.raises(UnknownSecurityError):
        SecCode.parse("00700.HK")
    code = SecCode.parse("00700.HK", sec_type="stock")
    assert code.canonical == "00700.HK"


def test_with_sec_type_returns_copy() -> None:
    code = SecCode.parse("000001.SZ")
    other = code.with_sec_type(SecType.ETF)
    assert other.sec_type is SecType.ETF
    assert code.sec_type is SecType.STOCK


def test_parse_codes_keeps_order() -> None:
    codes = parse_codes(["600000.SH", "000001.OF"])
    assert [c.canonical for c in codes] == ["600000.SH", "000001.OF"]
    assert parse_codes("600000.SH")[0].canonical == "600000.SH"
