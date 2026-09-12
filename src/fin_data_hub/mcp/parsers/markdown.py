"""Markdown 表格解析（iFinD NL 工具返回 ``answer`` 文本）。

iFinD 的 NL 响应形如::

    |证券代码|证券简称|收盘价（单位：元）|
    |---|---|---|
    |000300.SH|沪深300|4510.1554|

一次响应可能包含多张表（如净值接口先给元信息表、再给数值表），
:func:`parse_markdown_tables` 会全部解析，由调用方按所需列选择。
"""

from __future__ import annotations

import re

import pandas as pd

_UNIT_FACTORS: tuple[tuple[str, float], ...] = (
    ("亿元", 1e8),
    ("万元", 1e4),
    ("千元", 1e3),
    ("元", 1.0),
    ("手", 100.0),
    ("股", 1.0),
)

_UNIT_PATTERN = re.compile(r"^(?P<base>.*?)[（(]单位[:：]\s*(?P<unit>[^）)]+)[）)]\s*$")


def split_unit(column: str) -> tuple[str, float]:
    """拆分带单位列名，返回 ``(基础列名, 换算系数)``。

    识别的单位：亿元/万元/千元/元、手/股；未识别时系数为 1.0。
    """
    match = _UNIT_PATTERN.match(column.strip())
    if not match:
        return column.strip(), 1.0
    base = match.group("base").strip()
    unit = match.group("unit").strip()
    for suffix, factor in _UNIT_FACTORS:
        if unit.endswith(suffix):
            return base, factor
    return base, 1.0


def _is_separator(cells: list[str]) -> bool:
    return all(cell and set(cell) <= set("-: ") for cell in cells)


def parse_markdown_tables(text: str) -> list[pd.DataFrame]:
    """解析文本中的所有 markdown 表格，返回 DataFrame 列表（保持出现顺序）。"""
    tables: list[pd.DataFrame] = []
    header: list[str] | None = None
    rows: list[list[str]] = []

    def flush() -> None:
        nonlocal header, rows
        if header is not None:
            tables.append(pd.DataFrame(rows, columns=header, dtype=object))
        header, rows = None, []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            flush()
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if header is None:
            header = cells
            continue
        if _is_separator(cells):
            continue
        rows.append(cells)
    flush()
    return tables


def find_table(
    tables: list[pd.DataFrame], required: tuple[str, ...]
) -> pd.DataFrame | None:
    """返回首个包含全部所需列（去除单位后）的表。"""
    for table in tables:
        bases = {split_unit(column)[0] for column in table.columns}
        if all(name in bases for name in required):
            return table
    return None
