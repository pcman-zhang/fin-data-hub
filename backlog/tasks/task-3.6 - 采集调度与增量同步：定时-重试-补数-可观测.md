---
id: TASK-3.6
title: 采集调度与增量同步：定时 / 重试 / 补数 / 可观测
status: To Do
assignee: []
created_date: '2026-09-13 06:01'
updated_date: '2026-09-13 06:17'
labels: []
milestone: m-0
dependencies:
  - TASK-3.1
  - TASK-3.3
parent_task_id: TASK-3
ordinal: 25000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
调度服务（已定 APScheduler + PostgreSQL job store）：按数据域配置同步频率与窗口、失败重试与断点补数、并发与限流复用 v0 机制、任务运行记录（job_runs）与可观测（指标/日志）；交易日历感知。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 定时任务可配置且幂等；失败自动重试与补数
- [ ] #2 运行记录可查询（任务/窗口/耗时/结果）
- [ ] #3 限流与成本预算在平台侧持续生效
<!-- AC:END -->
