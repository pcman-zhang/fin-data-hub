import pytest

import fin_data_hub
from fin_data_hub import Source


def test_version_is_exported() -> None:
    assert fin_data_hub.__version__


def test_version_matches_package_metadata() -> None:
    from importlib.metadata import PackageNotFoundError, version

    try:
        installed = version("fin-data-hub")
    except PackageNotFoundError:
        pytest.skip("包未安装（metadata 不可用）")
    assert installed == fin_data_hub.__version__


def test_source_enum_values() -> None:
    assert {s.value for s in Source} == {"tushare", "wind", "ifind", "akshare", "fuyao"}


def test_source_is_str() -> None:
    assert Source.TUSHARE == "tushare"


def test_public_errors_derive_from_base() -> None:
    from fin_data_hub import (
        MissingCredentialError,
        NetworkError,
        RateLimitError,
        RateLimitTimeout,
        ResponseParseError,
        SourceError,
        UnknownSecurityError,
        UnsupportedCapability,
    )

    for exc in (
        MissingCredentialError,
        NetworkError,
        RateLimitError,
        RateLimitTimeout,
        ResponseParseError,
        SourceError,
        UnknownSecurityError,
        UnsupportedCapability,
    ):
        assert issubclass(exc, fin_data_hub.FinDataHubError)


def test_error_builtin_subclasses() -> None:
    from fin_data_hub import RateLimitTimeout, UnknownSecurityError

    assert issubclass(UnknownSecurityError, ValueError)
    assert issubclass(RateLimitTimeout, TimeoutError)

    with pytest.raises(ValueError):
        raise UnknownSecurityError("bad code")
