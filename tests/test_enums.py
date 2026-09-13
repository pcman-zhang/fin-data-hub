import pytest

from fin_data_hub import Currency, SecCode, Venue
from fin_data_hub.constants import currency_for_code, currency_for_venue
from fin_data_hub.errors import UnknownSecurityError


def test_venue_currency_map() -> None:
    assert currency_for_venue(Venue.SH) is Currency.CNY
    assert currency_for_venue("HK") is Currency.HKD
    assert currency_for_venue("O") is Currency.USD
    assert currency_for_venue("N") is Currency.USD
    assert currency_for_venue("GI") is None  # 需参考数据判定


def test_currency_for_code() -> None:
    assert currency_for_code("600000.SH") is Currency.CNY
    assert currency_for_code("00700.HK") is Currency.HKD
    assert currency_for_code("AAPL.O") is Currency.USD
    assert currency_for_code("SPX.GI") is None
    assert currency_for_code("600000") is None


def test_new_venues_inference() -> None:
    assert SecCode.parse("AAPL.O").sec_type.value == "stock"
    assert SecCode.parse("SPX.GI").sec_type.value == "index"
    assert SecCode.parse("885800.TI").sec_type.value == "index"
    assert SecCode.parse("881155.WI").sec_type.value == "index"
    assert SecCode.parse("000300.CSI").sec_type.value == "index"


def test_hk_requires_explicit_sec_type() -> None:
    with pytest.raises(UnknownSecurityError):
        SecCode.parse("00700.HK")
    assert SecCode.parse("00700.HK", sec_type="stock").canonical == "00700.HK"


def test_unknown_venue_message_lists_venues() -> None:
    with pytest.raises(UnknownSecurityError, match="未知 venue"):
        SecCode.parse("600000.XX")
