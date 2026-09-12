---
id: TASK-2
title: 实现 v0 数据聚合库（doc-1 架构落地）
status: To Do
assignee: []
created_date: '2026-09-12 12:00'
labels: []
dependencies: []
documentation:
  - backlog/docs/architecture/doc-1 - 多源金融数据聚合库-v0-架构设计.md
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
按 Backlog 文档 doc-1 落地 fin-data-hub v0：统一 WindCode、统一接口（显式 source）、配置注入、每源限流与配额计量、并发安全、TTL 内存缓存（force）。不含持久化存储层；iFinD/Wind 经厂商远端 MCP（HTTP JSON-RPC）接入，不使用厂商 SDK。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 库可通过 pip install -e 安装并 import fin_data_hub
- [ ] #2 pytest 全绿；核心模块有单元测试
- [ ] #3 无任何持久化写盘；缓存仅进程内内存
- [ ] #4 iFinD/Wind 适配器不依赖厂商 SDK
<!-- AC:END -->
