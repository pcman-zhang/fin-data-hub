---
id: TASK-2.10
title: 成本与配额计量、预算告警
status: To Do
assignee: []
created_date: '2026-09-12 12:02'
labels: []
dependencies:
  - TASK-2.4
parent_task_id: TASK-2
ordinal: 12000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
每源调用计数器（按次/按积分）；调用记录（source/endpoint/codes/latency/est_cost）；预算阈值可配置并告警；hub.stats() 暴露。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 调用计数在 FakeAdapter 与真实适配器路径均生效；stats() 返回 calls/cost 等
- [ ] #2 预算阈值触发告警（日志/回调策略）有测试
- [ ] #3 计数器线程安全
<!-- AC:END -->
