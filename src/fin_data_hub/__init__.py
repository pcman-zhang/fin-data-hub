"""fin-data-hub：多源金融数据聚合库。"""

from fin_data_hub._version import __version__
from fin_data_hub.cache import MemoryCache
from fin_data_hub.codes import SecCode, SecType, parse_codes
from fin_data_hub.config import (
    AkShareConfig,
    CacheConfig,
    HubConfig,
    IfindConfig,
    TushareConfig,
    WindConfig,
)
from fin_data_hub.enums import Source
from fin_data_hub.errors import (
    FinDataHubError,
    MissingCredentialError,
    NetworkError,
    RateLimitError,
    RateLimitTimeout,
    ResponseParseError,
    SourceError,
    UnknownSecurityError,
    UnsupportedCapability,
)
from fin_data_hub.facade import DataHub
from fin_data_hub.sources import BaseAdapter, SourceRegistry

__all__ = [
    "__version__",
    "Source",
    "SecCode",
    "SecType",
    "parse_codes",
    "DataHub",
    "HubConfig",
    "CacheConfig",
    "TushareConfig",
    "WindConfig",
    "IfindConfig",
    "AkShareConfig",
    "MemoryCache",
    "BaseAdapter",
    "SourceRegistry",
    "FinDataHubError",
    "MissingCredentialError",
    "NetworkError",
    "RateLimitError",
    "RateLimitTimeout",
    "ResponseParseError",
    "SourceError",
    "UnknownSecurityError",
    "UnsupportedCapability",
]
