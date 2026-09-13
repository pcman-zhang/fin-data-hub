"""归一化 Spec：加载、校验与响应归一化（doc-6 §4）。

每个数据源一个 TOML（本包目录内），声明：

- ``[params]``：请求参数映射（复权枚举、日期格式等）；
- ``[response.<capability>]``：原始响应字段 → canonical 字段的映射
  （``type`` ∈ code/date/date_ms/float/int/str/bool，``factor`` 支持单位换算）。

v0 阶段：spec 作为**契约与校验**（覆盖度、结构、归一化语义测试）；
阶段 B 由 adapter 切换为调用 :func:`normalize`。
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from importlib.resources import files

import pandas as pd

from fin_data_hub.enums import Source
from fin_data_hub.errors import ResponseParseError

_FIELD_TYPES = frozenset({"code", "date", "date_ms", "float", "int", "str", "bool"})


@dataclass(frozen=True, slots=True)
class FieldSpec:
    source: str
    type: str = "float"
    factor: float = 1.0
    format: str | None = None


@dataclass(frozen=True, slots=True)
class ResponseSpec:
    required: tuple[str, ...]
    fields: dict[str, FieldSpec]


@dataclass(frozen=True, slots=True)
class SourceSpec:
    source: Source
    params: dict[str, dict[str, str]]
    responses: dict[str, ResponseSpec]


def load_spec(source: Source | str) -> SourceSpec:
    """加载某数据源的 spec（``fin_data_hub/specs/<source>.toml``）。"""
    resolved = Source(source)
    resource = files("fin_data_hub.specs").joinpath(f"{resolved.value}.toml")
    data = tomllib.loads(resource.read_text(encoding="utf-8"))
    responses: dict[str, ResponseSpec] = {}
    for endpoint, block in (data.get("response") or {}).items():
        fields = {
            canonical: FieldSpec(
                source=spec["source"],
                type=spec.get("type", "float"),
                factor=float(spec.get("factor", 1.0)),
                format=spec.get("format"),
            )
            for canonical, spec in (block.get("fields") or {}).items()
        }
        responses[endpoint] = ResponseSpec(
            required=tuple(block.get("required", [])), fields=fields
        )
    params = {
        group: {key: str(value) for key, value in values.items()}
        for group, values in (data.get("params") or {}).items()
    }
    return SourceSpec(source=resolved, params=params, responses=responses)


def load_all_specs() -> dict[Source, SourceSpec]:
    """加载全部 spec（缺失的源不包含在结果中）。"""
    specs: dict[Source, SourceSpec] = {}
    for source in Source:
        try:
            specs[source] = load_spec(source)
        except FileNotFoundError:
            continue
    return specs


def validate_specs(specs: dict[Source, SourceSpec] | None = None) -> list[str]:
    """结构性校验：返回错误列表（空列表 = 通过）。"""
    resolved = specs if specs is not None else load_all_specs()
    errors: list[str] = []
    for source, spec in resolved.items():
        if not spec.responses:
            errors.append(f"{source}: 无 response 映射")
        for endpoint, response in spec.responses.items():
            if not response.required:
                errors.append(f"{source}.{endpoint}: required 为空")
            if not response.fields:
                errors.append(f"{source}.{endpoint}: fields 为空")
            for canonical, field in response.fields.items():
                if field.type not in _FIELD_TYPES:
                    errors.append(
                        f"{source}.{endpoint}.{canonical}: 未知 type={field.type!r}"
                    )
                if field.factor <= 0:
                    errors.append(
                        f"{source}.{endpoint}.{canonical}: factor 必须为正"
                    )
    return errors


def normalize(
    raw: pd.DataFrame,
    spec: ResponseSpec,
    *,
    source: Source | str,
) -> pd.DataFrame:
    """按 spec 将原始响应归一化为 canonical DataFrame。"""
    source_name = str(source)
    missing = [column for column in spec.required if column not in raw.columns]
    if missing:
        raise ResponseParseError(
            f"[{source_name}] 原始响应缺少字段 {missing}；实际: {list(raw.columns)}"
        )
    data: dict[str, pd.Series] = {}
    for canonical, field in spec.fields.items():
        if field.source not in raw.columns:
            raise ResponseParseError(
                f"[{source_name}] 缺少映射源字段 {field.source!r}（canonical={canonical}）"
            )
        series = raw[field.source]
        parsed: pd.Series
        if field.type == "date":
            parsed = pd.to_datetime(series, format=field.format)
        elif field.type == "date_ms":
            parsed = (
                pd.to_datetime(series, unit="ms", utc=True)
                .dt.tz_convert("Asia/Shanghai")
                .dt.normalize()
                .dt.tz_localize(None)
            )
        elif field.type == "float":
            parsed = pd.to_numeric(series, errors="coerce") * field.factor
        elif field.type == "int":
            parsed = pd.to_numeric(series, errors="coerce").astype("Int64")
        elif field.type == "bool":
            parsed = series.astype(bool)
        else:  # code / str
            parsed = series.astype(str)
        data[canonical] = parsed
    frame = pd.DataFrame(data)
    for canonical, field in spec.fields.items():
        if field.type in ("date", "date_ms"):
            frame[canonical] = frame[canonical].astype("datetime64[ns]")
    return frame
