"""数据库文档生成（Schema First）：表/字段/依赖 → Markdown。

由字典 + Security Master schema 自动生成，保证文档与 DDL 同源（doc-11 §7）。
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Column

from fin_data_platform.dictionary import DEFAULT_ROOT
from fin_data_platform.dictionary.models import DatasetSpec
from fin_data_platform.storage.schema import build_metadata

_REF_TABLES = {
    "ref.security_master": "标的注册主数据（SCD2；含退市）",
    "ref.security_alias": "多源代码映射（source + source_code + 有效期）",
    "ref.security_status_history": "状态区间历史（L/P/D）",
    "ref.security_attribute_history": "属性区间历史（名称/ST 等 SCD2）",
}


def _purpose(dataset: str, spec: DatasetSpec | None) -> str:
    if spec is not None:
        return spec.description
    return _REF_TABLES.get(dataset, "")


def _column_type(column: Column) -> str:
    return str(column.type)


def database_markdown(root: Path | None = None) -> str:
    """生成数据库设计文档（表作用 / 字段与类型 / 依赖关系）。"""
    metadata, specs = build_metadata(root or DEFAULT_ROOT)
    lines: list[str] = [
        "# 数据库设计：表 / 字段 / 依赖（自动生成）",
        "",
        "> 由数据字典与 Security Master schema 生成（Schema First）；请勿手改，变更走字典。",
        "",
        "## 1. 表清单与作用",
        "",
        "| 表 | 作用 | 物理键 | 分区策略 |",
        "|---|---|---|---|",
    ]
    by_dataset = {spec.storage.canonical_table: (dataset, spec) for dataset, spec in specs.items()}
    table_order = sorted(metadata.tables, key=lambda key: (key.split(".")[0], key))
    for key in table_order:
        dataset, spec = by_dataset.get(key, (key, None))
        pk = ", ".join(column.name for column in metadata.tables[key].primary_key)
        strategy = spec.storage.partition_strategy if spec else "—"
        lines.append(f"| `{key}` | {_purpose(dataset, spec)} | {pk} | {strategy} |")

    lines += ["", "## 2. 字段与类型", ""]
    for key in table_order:
        dataset, spec = by_dataset.get(key, (key, None))
        table = metadata.tables[key]
        lines.append(f"### `{key}`")
        lines.append("")
        lines.append("| 字段 | 类型 | 可空 | 单位 | PIT 角色 | 说明 |")
        lines.append("|---|---|---|---|---|---|")
        field_by_name = {field.name: field for field in (spec.fields if spec else [])}
        for column in table.columns:
            field = field_by_name.get(column.name)
            unit = (field.unit if field else None) or ""
            pit = field.pit_role if field else ""
            description = field.description if field else ""
            nullable = "是" if column.nullable else "否"
            lines.append(
                f"| `{column.name}` | `{_column_type(column)}` | {nullable} | "
                f"{unit} | {pit} | {description} |"
            )
        lines.append("")

    lines += ["## 3. 表依赖关系（逻辑，无物理外键；doc-13 §4）", ""]
    for key in table_order:
        dataset, spec = by_dataset.get(key, (key, None))
        dependencies: list[str] = []
        if spec is not None:
            dependencies.extend(
                f"{ref.dataset}（血缘）" for ref in spec.lineage.upstream
            )
            for entry in spec.derived or []:
                dependencies.extend(
                    f"{ref.rpartition('.')[0]}（派生输入）" for ref in entry.inputs
                )
        table = metadata.tables[key]
        if any(
            column.name == "security_id" or column.name.endswith("_security_id")
            for column in table.columns
        ) and key != "ref.security_master":
            dependencies.append("ref.security_master（security_id 逻辑引用）")
        if key in (
            "ref.security_alias",
            "ref.security_status_history",
            "ref.security_attribute_history",
        ):
            dependencies.append("ref.security_master（security_id 逻辑引用）")
        unique = sorted(set(dependencies))
        lines.append(f"- `{key}` ← {'；'.join(unique) if unique else '—（源数据）'}")
    lines.append("")
    return "\n".join(lines)
