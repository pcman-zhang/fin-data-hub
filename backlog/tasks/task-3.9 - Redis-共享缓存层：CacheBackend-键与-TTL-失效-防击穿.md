---
id: TASK-3.9
title: Redis 共享缓存层：CacheBackend / 键与 TTL / 失效 / 防击穿
status: To Do
assignee: []
created_date: '2026-09-13 06:14'
updated_date: '2026-09-13 08:34'
labels: []
milestone: m-0
dependencies:
  - TASK-3.1
parent_task_id: TASK-3
ordinal: 28000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
平台 L2 共享缓存：CacheBackend 抽象（内存/Redis 实现）；键设计 fdh:{domain}:{panel}:{as_of|knowledge_time}:{params_hash}；按域 TTL 与同步后失效；Redis 锁实现跨进程 single-flight；值序列化（Arrow/Parquet 字节或 JSON + schema 版本）；命中率/内存指标可观测。v0 库保持内存缓存不变。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 CacheBackend 抽象与 Redis 实现落地；L1（进程内）+ L2（Redis）分层生效
- [ ] #2 缓存键含 PIT 语义（as-of/知识时间），无前视与陈旧混用
- [ ] #3 同步完成触发按域失效；跨进程 single-flight 防击穿
- [ ] #4 命中率/内存/失效指标可观测（供 WebUI/告警）
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
参数定稿（2026-09-13）：单机 2GB 上限 + volatile-lru；纯缓存可关持久化；代际版本号失效；Arrow IPC 序列化（小对象 JSON）；fail-open 直查；观测命中率/内存/淘汰/锁等待。
<!-- SECTION:NOTES:END -->
