"""引用注册表（doc-10 §3.3）：实体身份、分类面、关系、外部标识与 PIT Universe。"""

from fin_data_platform.registry.models import (
    BuildStats,
    CodeHistoryRecord,
    EntityClass,
    EntityRecord,
    EntityType,
    ExternalIdRecord,
    IdType,
    LifecycleRecord,
    LifecycleStatus,
    Market,
    RelationRecord,
    RelationTypeRecord,
    SocialStatus,
)
from fin_data_platform.registry.relation_types import (
    DEFAULT_RELATION_TYPES,
    load_relation_types,
    validate_relation_types,
)
from fin_data_platform.registry.repository import (
    EntityRegistryRepository,
    InMemoryEntityRegistryRepository,
)
from fin_data_platform.registry.service import EntityRegistry
from fin_data_platform.registry.universe import universe

__all__ = [
    "BuildStats",
    "CodeHistoryRecord",
    "DEFAULT_RELATION_TYPES",
    "EntityClass",
    "EntityRecord",
    "EntityRegistry",
    "EntityRegistryRepository",
    "EntityType",
    "ExternalIdRecord",
    "IdType",
    "InMemoryEntityRegistryRepository",
    "LifecycleRecord",
    "LifecycleStatus",
    "Market",
    "RelationRecord",
    "RelationTypeRecord",
    "SocialStatus",
    "load_relation_types",
    "universe",
    "validate_relation_types",
]
