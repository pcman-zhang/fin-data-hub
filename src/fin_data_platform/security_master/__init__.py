"""Security Master（doc-10 §3.3）：标的注册、多源代码映射、as-of 宇宙与属性还原。"""

from fin_data_platform.security_master.master import SecurityMaster
from fin_data_platform.security_master.models import (
    AliasRecord,
    AttributeInterval,
    BuildStats,
    SecurityRecord,
    StatusInterval,
)
from fin_data_platform.security_master.repository import (
    InMemorySecurityMasterRepository,
    SecurityMasterRepository,
)

__all__ = [
    "AliasRecord",
    "AttributeInterval",
    "BuildStats",
    "InMemorySecurityMasterRepository",
    "SecurityMaster",
    "SecurityMasterRepository",
    "SecurityRecord",
    "StatusInterval",
]
