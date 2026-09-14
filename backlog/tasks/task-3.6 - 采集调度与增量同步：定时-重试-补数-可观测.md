---
id: TASK-3.6
title: 采集调度与增量同步：定时 / 重试 / 补数 / 可观测
status: Done
assignee: []
created_date: '2026-09-13 06:01'
updated_date: '2026-09-14 14:10'
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
- [x] #1 定时任务可配置且幂等；失败自动重试与补数
- [x] #2 运行记录可查询（任务 / 窗口 / 耗时 / 结果）
- [x] #3 限流与成本预算在 Runtime 进程内持续生效（跨进程聚合独立为 TASK-3.19，增强项）
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

切片 3 启动（2026-09-14）：生产组合装配——SyncSettings（FDP_SYNC_CODES/START/SOURCE/SCHEDULE + TUSHARE_TOKEN）→ build_sync_runtime 组装 Hub/任务注册/日历/水位 provider → entrypoint 配置驱动启动；README 记录配置项。

切片 3 完成（2026-09-14，配置驱动装配）：① ingestion/settings.py::SyncSettings（FDP_SYNC_CODES/START/SOURCE/SCHEDULE 解析与校验，ISO 日期严格化）；② ingestion/bootstrap.py::build_sync_runtime（Hub 凭证注入 → 任务注册 → 日历 → 水位 provider → RuntimeApp；未配置时返回空 Runtime）；③ entrypoint 接入：配置驱动启动并记录装配信息，配置非法退出码 2；④ README 增加「运行 Runtime」配置说明；⑤ 验证：366 单测（新增 bootstrap 3 项）+ 12 PG 集成（含配置驱动 entrypoint 子进程端到端：入队→执行→水位推进；sync 文件连跑 2 次）+ ruff/mypy 全绿。

切片 3 完成（配置驱动装配）：SyncSettings（FDP_SYNC_CODES/START/SOURCE 必填/SCHEDULE 预校验）→ build_sync_runtime 组装 → entrypoint 配置驱动启动；README 配置说明。复审修复 3 项。验证：366 单测 + 12 PG 集成（含配置驱动 entrypoint 子进程端到端，连续 2 次）+ ruff/mypy 全绿。AC3 按进程内口径收口；跨进程聚合独立为 TASK-3.19（依赖 TASK-3.9）。
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @review
created: 2026-09-14 13:16
---
切片 1 复审修复（6 项，全部落地）：① entity_id 分配改全局 advisory lock（不同代码并发曾会分到相同 id，且 daily_bar 冲突静默丢行；新增 PG 并发唯一性回归测试）；② 实现修订语义（值变化→新版本 knowledge_time=修订时刻，历史保留；值未变不写），不再依赖 ON CONFLICT 静默跳过；③ 集成测试改为增量断言 + 清理本 job 运行记录，可重复执行（已连跑两次）；④ build_metadata 进程内缓存（_daily_bar_table）；⑤ registry/__init__ 不再导出 store（避免 registry 包引入 SQLAlchemy 硬依赖）；⑥ 任务执行改用注册 code 并校验 scope 不一致即报错。验证：356 单测 + 10 PG 集成（含并发分配、修订、扩窗补数）+ ruff/mypy 全绿。
---

author: @review
created: 2026-09-14 13:45
---
切片 2 复审修复（8 项，全部落地）：① cron 触发器显式 timezone=UTC（此前默认本地时区）；② 新增 advance_watermark 单调推进（乱序/补数窗口不回退水位）；③ 调度判定截止改为 16:30 CST（08:30 UTC，等源端发布），并对「窗口末日=今日且零行」保留今日待重试（防缺口永不回补）；④ 混合注册表：未配置 schedule 的任务仍由轮询线程处理（Scheduler.run 增加 only 过滤）；⑤ APScheduler 模式 scheduler health 补齐（alive/last_tick/intents/last_error）；⑥ 启动时 reconcile 清理 job store 陈旧注册；⑦ 集成测试水位断言改为单调语义 + succeeded/水位双双就绪等待；⑧ on_success 第三参类型收紧为 MetaRepository（去掉 type: ignore）。验证：363 单测 + 11 PG 集成（sync 文件连跑 2 次、调度文件连跑 6 次全绿）+ ruff/mypy 全绿。
---

author: @review
created: 2026-09-14 14:07
---
切片 3 复审修复（3 项）：① FDP_SYNC_SOURCE 改为必填并校验已知数据源（Hub 不做隐式路由；此前缺省会导致启动成功但永不产生任务且无日志），配置错误统一 exit 2；② README/文案纠正「缺省为轮询追平」（并非仅手动）；③ FDP_SYNC_SCHEDULE 预校验（cron 段数/interval 数值），非法配置干净退出。验证：366 单测 + 12 PG 集成（连续 2 次）+ ruff/mypy 全绿；手工验证缺 source / 非法 schedule 均 exit 2 且错误信息明确。
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
采集调度与增量同步落地（三切片）：① 单标的 sync 闭环（Security Master 最小持久化 + 幂等写入 + 修订版本）；② APScheduler 调度（PG job store）+ 交易日历 + 水位窗口/断点补数；③ 配置驱动 Runtime 装配（FDP_SYNC_* 环境变量 + entrypoint）。限流与预算按进程内口径生效（跨进程聚合 → TASK-3.19）；运行记录在 meta.job_runs 可查询。验证：366 单测 + 12 PG 集成（真实 Tushare 落库/调度/配置驱动启动）+ ruff/mypy 全绿。
<!-- SECTION:FINAL_SUMMARY:END -->
