---
id: TASK-3.18
title: FinDataRuntime 骨架：角色分层入口 / 任务与依赖框架 / 健康检查
status: To Do
assignee: []
created_date: '2026-09-14 12:25'
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
- [ ] #1 runtime 入口可启动：配置加载 / 字典 CI 校验 / 迁移版本一致检查（不一致 fail fast）；角色分层启动且健康检查可探测
- [ ] #2 任务框架落地：meta.job_defs / meta.job_dependencies / meta.job_runs / meta.watermarks schema 与迁移；声明式注册与状态机
- [ ] #3 幂等与并发：幂等键规则（仅 derive / build_rm 版本维度）+ PG advisory lock；重复触发安全（测试覆盖）
- [ ] #4 依赖门控：parent 成功才放行 child（示例链），父失败不放行；Dispatcher 有界队列 / 优先级生效
- [ ] #5 进程可拆：runtime-scheduler / runtime-worker 入口可独立启动并仅凭 PostgreSQL 协调（本地验证）
- [ ] #6 文档（doc-20）与测试同步；pytest / ruff / mypy 通过
<!-- AC:END -->
