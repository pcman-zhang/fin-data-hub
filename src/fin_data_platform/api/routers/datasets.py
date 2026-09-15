"""数据集（数据字典）浏览：只读，直接来自字典（不依赖数据库）。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from fin_data_platform.api.deps import ApiContext, get_context
from fin_data_platform.api.schemas import DatasetDetail, DatasetSummary

Context = Annotated[ApiContext, Depends(get_context)]

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("", response_model=list[DatasetSummary], summary="数据集清单")
def list_datasets(
    context: Context,
    domain: Annotated[str | None, Query(description="按数据域过滤")] = None,
    q: Annotated[str | None, Query(description="按数据集名/描述模糊匹配")] = None,
) -> list[DatasetSummary]:
    specs = list(context.specs.values())
    if domain:
        specs = [spec for spec in specs if spec.domain == domain]
    if q:
        needle = q.strip().lower()
        specs = [
            spec
            for spec in specs
            if needle in spec.dataset.lower() or needle in spec.description.lower()
        ]
    return [
        DatasetSummary.from_spec(spec)
        for spec in sorted(specs, key=lambda item: item.dataset)
    ]


@router.get("/{dataset}", response_model=DatasetDetail, summary="数据集详情")
def get_dataset(dataset: str, context: Context) -> DatasetDetail:
    spec = context.specs.get(dataset)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"数据集不存在: {dataset}")
    return DatasetDetail.from_spec(spec)
