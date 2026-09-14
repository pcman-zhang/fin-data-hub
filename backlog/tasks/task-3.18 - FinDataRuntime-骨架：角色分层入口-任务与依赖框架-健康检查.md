---
id: TASK-3.18
title: FinDataRuntime 骨架：角色分层入口 / 任务与依赖框架 / 健康检查
status: Done
assignee: []
created_date: '2026-09-14 12:25'
updated_date: '2026-09-14 12:51'
labels: []
milestone: m-0
dependencies: []
parent_task_id: TASK-3
ordinal: 56000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
按 doc-20《FinDataRuntime：控制面 Runtime 与任务模型》落地 Runtime 骨架（控制面常驻进程），作为采集调度（TASK-3.6）、派生执行（TASK-3.12）、质量执行（TASK-3.5）、L2 缓存（TASK-3.9）的宿主；TASK-3.4 负责其容器化部署。

范围：
1. 单镜像多入口：runtime / runtime-scheduler / runtime-worker / rest / admin；配置与凭证注入（不落镜像）；
2. 角色分层：Scheduler（只入队、不等待）/ Dispatcher（依赖门控 + 优先级 + 有界队列背压）/ WorkerPool（只执行）；层间显式接口，无共享可变状态；各角色独立健康检查（隔离原则）；
3. 任务与依赖框架：声明式 job_defs 注册；meta.job_defs / meta.job_dependencies / meta.job_runs / meta.watermarks 等表与迁移；状态机（queued/running/succeeded/failed/retrying/dead/interrupted）；幂等键（仅 derive→algorithm_id、build_rm→读模型 semantic_version 两处版本维度）；PG advisory lock；重试 / 水位 / 补数；
4. 启动检查：迁移版本一致 fail fast、字典 CI 校验通过才启动；依赖注册与恢复（watermark / 失败重试）；
5. 可观测：结构化日志（request_id 贯穿）、按角色健康检查、job_runs 查询。

明确不做（doc-20 §10）：DAG 编排（分支 / 汇合 / 动态展开 / 回填传播）、分布式调度与多副本选举、事件驱动工作流、实时流式摄取。

设计依据：doc-20（已定稿）。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 runtime 入口可启动：配置加载 / 字典 CI 校验 / 迁移版本一致检查（不一致 fail fast）；角色分层启动且健康检查可探测
- [x] #2 任务框架落地：meta.job_defs / meta.job_dependencies / meta.job_runs / meta.watermarks schema 与迁移；声明式注册与状态机
- [x] #3 幂等与并发：幂等键规则（仅 derive / build_rm 版本维度）+ PG advisory lock；重复触发安全（测试覆盖）
- [x] #4 依赖门控：parent 成功才放行 child（示例链），父失败不放行；Dispatcher 有界队列 / 优先级生效
- [x] #5 进程可拆：runtime-scheduler / runtime-worker 入口可独立启动并仅凭 PostgreSQL 协调（本地验证）
- [x] #6 文档（doc-20）与测试同步；pytest / ruff / mypy 通过
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. meta schema：runtime/schema.py 定义 meta.job_defs / job_dependencies / job_runs / watermarks；合并进 build_metadata（include_runtime 参数）；新增 Alembic 修订 0002_runtime_meta（基线冻结，增量走修订）+ 漂移校验。
2. 任务域：models（JobKind/JobStatus/JobDef/JobRun/Watermark）、keys（幂等键，仅 derive→algorithm_id / build_rm→semantic_version 版本维度）、registry（@task 声明式注册 + 依赖声明）、repository（MetaRepository 协议 + 内存 + SQLAlchemy 实现；advisory lock）。
3. 角色分层：Scheduler（只入队）/ Dispatcher（依赖门控 + 优先级 + 有界队列背压）/ WorkerPool（执行）；显式队列接口、无共享可变状态；Runtime 编排 + 按角色健康检查。
4. 入口与启动检查：python -m fin_data_platform.runtime --role all|scheduler|worker；配置注入；迁移版本一致 fail fast；字典 CI 校验。
5. 测试：幂等键/状态机/并发锁/依赖门控/背压/角色可拆（SQLite + 内存）；迁移与存储测试更新；PG 集成补充 meta 表。
6. 文档同步：doc-17 重生成、README 架构节纳入 Runtime；全量 pytest/ruff/mypy；任务收口。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
实现：① meta 控制面 4 表（job_defs/job_dependencies/job_runs/watermarks）+ Alembic 修订 0002（基线冻结，新增漂移校验）；② 幂等键 job_key 仅 derive→algorithm_id / build_rm→semantic_version 版本维度；③ 角色分层 Scheduler（只入队）/ Dispatcher（依赖门控 + 背压）/ WorkerPool（原子领取执行），层间仅经 meta 协调、无共享可变状态；④ 状态机 queued/running/succeeded/failed/retrying/dead/interrupted，失败退避与 attempt 递增、父失败不放行；⑤ 入口 python -m fin_data_platform.runtime --role all|scheduler|worker，readiness（DB/字典/迁移版本）fail fast；⑥ 健康输出按角色（tick/队列/池/最近错误）。验证：347 单测；PG 集成 7 passed（含迁移 0002、仓储往返、并发领取互斥、入口冒烟）；ruff/mypy 全绿；doc-17 重生成、doc-20 落位与 README 控制面同步。
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @review
created: 2026-09-14 12:51
---
复审修复（6 项，全部落地）：① sync_defs/sync_dependencies 改为全集替换（修复依赖清空后旧行残留导致 child 永久门控）；② 新增 interrupt_running 并在 WorkerPool.stop 超时后回收本进程 running 行（worker 名带 PID 前缀，防跨进程误伤）；③ readiness 的迁移版本检查兜底异常，DB 不可达不再抛栈；④ Scheduler/Worker 循环兜底捕获仓储异常（线程不再静默死亡，错误入健康输出）；⑤ claim 的 advisory lock 改为 (dataset, scope) 粒度并修正注释；⑥ 幂等键会话语义：create 重置 attempt=1（去掉 (job_key, attempt) 唯一约束），dead 重放恢复完整重试预算；另：_finish 增加 running 状态守卫，超时回收后不被迟到结果改写。验证：352 单测（新增 5 项复审回归）+ 8 PG 集成（迁移 0002 重新生成后全链路）+ ruff/mypy 全绿。
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
FinDataRuntime 骨架落地：meta 控制面 schema（修订 0002）与状态权威、幂等键（仅 derive/build_rm 版本维度）、Scheduler/Dispatcher/WorkerPool 角色分层（可拆进程入口、无共享可变状态）、依赖门控与有界队列背压、advisory lock 并发防重、readiness fail fast；文档（doc-17/20、README）同步。验证：347 单测 + 7 PG 集成（含并发互斥与入口冒烟）+ ruff/mypy 全绿。
<!-- SECTION:FINAL_SUMMARY:END -->
