"""任务与水位：运行记录查询 + 同步意图提交（写 ``meta`` 队列，Runtime 执行）。

控制面数据使用写连接（平台内部写入端）；同步触发不直接调用采集，
仅提交意图，由 scheduler/worker 认领（避免绕过控制面）。
"""

from __future__ import annotations

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from fin_data_platform.api.deps import ApiContext, get_context
from fin_data_platform.api.schemas import (
    JobRunOut,
    SyncItem,
    SyncRequest,
    SyncResponse,
    WatermarkOut,
)
from fin_data_platform.runtime._util import utcnow
from fin_data_platform.runtime.models import JobIntent, JobKind, JobStatus

router = APIRouter(tags=["jobs"])

Context = Annotated[ApiContext, Depends(get_context)]

_STATUS_PATTERN = "|".join(status.value for status in JobStatus)


@router.get("/jobs", response_model=list[JobRunOut], summary="任务运行记录")
def list_jobs(
    context: Context,
    status: Annotated[str | None, Query(pattern=f"^({_STATUS_PATTERN})$")] = None,
    job_id: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[JobRunOut]:
    runs = context.meta.list_runs(status=status, job_id=job_id, limit=limit)
    return [JobRunOut.from_run(run) for run in runs]


@router.get("/jobs/{run_id}", response_model=JobRunOut, summary="任务详情")
def get_job(run_id: int, context: Context) -> JobRunOut:
    run = context.meta.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"任务运行不存在: {run_id}")
    return JobRunOut.from_run(run)


@router.get("/watermarks", response_model=list[WatermarkOut], summary="数据水位")
def list_watermarks(context: Context) -> list[WatermarkOut]:
    return [
        WatermarkOut.from_watermark(mark) for mark in context.meta.list_watermarks()
    ]


@router.post(
    "/jobs/sync",
    response_model=SyncResponse,
    status_code=202,
    summary="触发同步（提交意图；WebUI 侧二次确认）",
)
def trigger_sync(payload: SyncRequest, context: Context) -> SyncResponse:
    known = {definition.job_id for definition in context.meta.list_defs()}
    today = utcnow().date()
    end = payload.end or today
    submitted: list[SyncItem] = []
    skipped: list[SyncItem] = []

    for code in dict.fromkeys(payload.codes):
        job_id = f"sync.{payload.dataset}.{code}"
        item = SyncItem(code=code, job_id=job_id, status="skipped")
        if job_id not in known:
            item.note = "任务未注册（检查代码拼写或调度配置）"
            skipped.append(item)
            continue
        start = payload.start
        if start is None:
            mark = context.meta.get_watermark(payload.dataset, scope=code)
            if mark is not None and mark.watermark_time is not None:
                start = mark.watermark_time.date() + timedelta(days=1)
            else:
                start = end
        item.window_start, item.window_end = start, end
        if start > end:
            item.note = f"窗口为空（{start} > {end}）"
            skipped.append(item)
            continue
        run = context.meta.create_run(
            JobIntent(
                kind=JobKind.SYNC.value,
                job_id=job_id,
                dataset=payload.dataset,
                scope=code,
                window_start=start,
                window_end=end,
                priority=payload.priority,
            ),
            request_id=payload.request_id,
        )
        if run is None:
            item.note = "重复意图（幂等键命中，已忽略）"
            skipped.append(item)
            continue
        item.run_id = run.run_id
        item.status = run.status
        submitted.append(item)

    return SyncResponse(submitted=submitted, skipped=skipped)
