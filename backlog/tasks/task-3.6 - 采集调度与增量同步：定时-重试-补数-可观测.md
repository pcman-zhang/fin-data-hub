---
id: TASK-3.6
title: 采集调度与增量同步：定时 / 重试 / 补数 / 可观测
status: In Progress
assignee: []
created_date: '2026-09-13 06:01'
updated_date: '2026-09-14 13:16'
labels: []
milestone: m-0
dependencies:
  - TASK-3.1
  - TASK-3.3
  - TASK-3.18
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

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
切片 1（最小实验，本次）：单标的日线 sync job 闭环
1. Security Master 最小持久化：registry/store.py::EntityStore.ensure_entity（ref.entity + code_history，advisory lock 防并发；补齐 TASK-3.14 延期项）。
2. Sync Engine：ingestion/daily_bar.py::sync_daily_bar（Hub.get_bars → canonical 行映射 → append_rows 幂等写入；PIT 字段 knowledge/ingest/version/provider）。
3. 任务注册：ingestion/tasks.py 把 sync job 挂到 Runtime TaskRegistry（scope=code，手动窗口触发）。
4. 验证：SQLite 单测（FakeHub 全链路 + 幂等重跑）+ PG 集成（真实 AkShare，单标的 600519.SH）。
切片 2（后续）：APScheduler 调度接入 + 交易日历窗口 + 水位/断点补数。
切片 3（后续）：限流/预算持续生效 + 运行记录查询 + 多标的/多数据集扩展。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
通知能力（2026-09-13，暂不制作）：调度/质量/新鲜度告警的主动通知见 doc-16（飞书等渠道）；首期不实现，依赖 WebUI 查看。

依赖更新（2026-09-14）：按 doc-20 增加前置 TASK-3.18（FinDataRuntime 骨架）；调度作为 Runtime 的 Scheduler/Dispatcher 角色实现，不再独立造进程。

切片 1 完成（2026-09-14，单标的 sync 实验）：① Security Master 最小持久化 registry/store.py::EntityStore（ref.entity + code_history，稳定 entity_id，PG advisory lock），补齐 TASK-3.14 延期项；② Sync Engine ingestion/daily_bar.py（Hub→canonical 映射 + append_rows 幂等；knowledge_time=交易日 15:00 CST 稳定值、ingest_time=物理入库，修复重跑产生新版本的语义错误）；③ 任务注册 ingestion/tasks.py（scope=code，Runtime submit → run_pending 闭环）；④ 验证：355 单测（新增 ingestion 3 项）+ 真实实验（Tushare 600519.SH 09-01~09-11：9 行落库、重复窗口 0 新增、扩窗补数 4 行、job_runs 记录）；ruff/mypy 全绿。剩余：APScheduler 定时接入、交易日历窗口、水位/断点补数自动化、成本预算平台侧生效。
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @review
created: 2026-09-14 13:16
---
切片 1 复审修复（6 项，全部落地）：① entity_id 分配改全局 advisory lock（不同代码并发曾会分到相同 id，且 daily_bar 冲突静默丢行；新增 PG 并发唯一性回归测试）；② 实现修订语义（值变化→新版本 knowledge_time=修订时刻，历史保留；值未变不写），不再依赖 ON CONFLICT 静默跳过；③ 集成测试改为增量断言 + 清理本 job 运行记录，可重复执行（已连跑两次）；④ build_metadata 进程内缓存（_daily_bar_table）；⑤ registry/__init__ 不再导出 store（避免 registry 包引入 SQLAlchemy 硬依赖）；⑥ 任务执行改用注册 code 并校验 scope 不一致即报错。验证：356 单测 + 10 PG 集成（含并发分配、修订、扩窗补数）+ ruff/mypy 全绿。
---
<!-- COMMENTS:END -->
