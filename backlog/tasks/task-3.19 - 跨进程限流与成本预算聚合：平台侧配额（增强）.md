---
id: TASK-3.19
title: 跨进程限流与成本预算聚合：平台侧配额（增强）
status: To Do
assignee: []
created_date: '2026-09-14 14:09'
labels: []
milestone: m-0
dependencies:
  - TASK-3.9
parent_task_id: TASK-3
ordinal: 57000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
背景：Hub 的令牌桶限流与预算统计为**进程内**生效；Runtime 支持 scheduler / worker 拆分进程（doc-20 §3.2）后，多进程总量不受控，付费源存在超预算风险。本任务作为增强项，将限额与预算聚合到平台侧共享层。

目标：
1. 基于 TASK-3.9（Redis CacheBackend）实现跨进程共享令牌 / 计数：多进程（runtime-scheduler / runtime-worker / 手工触发）下按源总量不超配；
2. 预算与告警按源聚合可查询（不再依赖单进程 hub.stats）；
3. 缓存不可用时 **fail-open**：回退进程内限额，采集不被阻塞（doc-10 §3.4 缓存非权威）；
4. 权威数据仍在 PostgreSQL；共享计数属可重建的运行时状态。

参考：doc-10 §3.4（缓存非权威 / fail-open）、doc-20 §4.5（并发与限流）、TASK-3.9。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 跨进程共享限流 / 计数（基于 TASK-3.9 CacheBackend）：多进程并发下按源总量不超配
- [ ] #2 预算与告警按源聚合可查询（多进程口径，不依赖单进程 stats）
- [ ] #3 缓存不可用时 fail-open：回退进程内限额且采集不阻塞；缓存恢复后自动接管
- [ ] #4 一致性测试（多客户端并发计数不超限）+ 文档同步；pytest/ruff/mypy 通过
<!-- AC:END -->
