"""fin-data-hub：多源金融数据聚合库。"""

from fin_data_hub._version import __version__
from fin_data_hub.cache import MemoryCache
from fin_data_hub.codes import SecCode, parse_codes
from fin_data_hub.config import (
    AkShareConfig,
    BaostockConfig,
    CacheConfig,
    FuyaoConfig,
    HubConfig,
    IfindConfig,
    TushareConfig,
    WindConfig,
)
from fin_data_hub.enums import (
    Adjust,
    Capability,
    Currency,
    Freq,
    ReferenceKind,
    SecType,
    Source,
    Venue,
)
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
from fin_data_hub.facade import FinDataHub
from fin_data_hub.routing import RoutingConfig
from fin_data_hub.sources import BaseAdapter, SourceRegistry
from fin_data_hub.usage import BudgetAlert, BudgetConfig, UsageLedger, UsageRecord

__all__ = [
    "__version__",
    "Source",
    "SecCode",
    "SecType",
    "Venue",
    "Currency",
    "Adjust",
    "Freq",
    "ReferenceKind",
    "Capability",
    "parse_codes",
    "FinDataHub",
    "HubConfig",
    "CacheConfig",
    "TushareConfig",
    "WindConfig",
    "IfindConfig",
    "AkShareConfig",
    "BaostockConfig",
    "FuyaoConfig",
    "MemoryCache",
    "RoutingConfig",
    "BaseAdapter",
    "SourceRegistry",
    "BudgetConfig",
    "BudgetAlert",
    "UsageLedger",
    "UsageRecord",
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
