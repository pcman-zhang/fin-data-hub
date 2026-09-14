"""关系词表加载与校验（doc-10 §3.3）。

词表是关系类型的唯一登记处：新增关系词必须先登记（CI 校验唯一性与反向对称）；
双向查询由 ``inverse_relation`` 元数据驱动（零硬编码）。
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import yaml

from fin_data_platform.registry.models import RelationTypeRecord

#: 词表文件（包内资源）
DEFAULT_RELATION_TYPES = Path(__file__).with_name("relation_types.yaml")


def load_relation_types(
    path: Path | None = None,
) -> dict[str, RelationTypeRecord]:
    """加载词表（结构校验；语义校验由 :func:`validate_relation_types` 承担）。"""
    target = path or DEFAULT_RELATION_TYPES
    data = yaml.safe_load(target.read_text(encoding="utf-8")) or []
    if not isinstance(data, list):
        raise ValueError(f"关系词表应为条目列表: {target}")
    records: dict[str, RelationTypeRecord] = {}
    for item in data:
        if not isinstance(item, dict):
            raise ValueError(f"关系词表条目应为对象: {item!r}")
        name = str(item.get("relation_type") or "").strip()
        inverse = str(item.get("inverse_relation") or "").strip()
        if not name or not inverse:
            raise ValueError(f"关系词条目缺少 relation_type/inverse_relation: {item!r}")
        if name in records:
            raise ValueError(f"关系词重复登记: {name}")
        records[name] = RelationTypeRecord(
            relation_type=name,
            inverse_relation=inverse,
            description=str(item.get("description") or ""),
        )
    return records


def validate_relation_types(
    records: Mapping[str, RelationTypeRecord],
) -> list[str]:
    """语义校验：反向词必须已登记，且反向关系对称（CI 门禁）。"""
    errors: list[str] = []
    for name, record in records.items():
        inverse = records.get(record.inverse_relation)
        if inverse is None:
            errors.append(f"{name}: inverse_relation 未登记（{record.inverse_relation}）")
        elif inverse.inverse_relation != name:
            errors.append(
                f"{name}: 反向不对称（{record.inverse_relation}.inverse_relation="
                f"{inverse.inverse_relation}）"
            )
    return errors
