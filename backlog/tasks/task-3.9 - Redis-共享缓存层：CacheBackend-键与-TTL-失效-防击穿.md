---
id: TASK-3.9
title: Redis 共享缓存层：CacheBackend / 键与 TTL / 失效 / 防击穿
status: Done
assignee:
  - '@freeman'
created_date: '2026-09-13 06:14'
updated_date: '2026-09-15 13:51'
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
- [x] #1 CacheBackend 抽象与 Redis 实现落地；L1（进程内）+ L2（Redis）分层生效
- [x] #2 缓存键含 PIT 语义（as-of/知识时间），无前视与陈旧混用
- [x] #3 同步完成触发按域失效；跨进程 single-flight 防击穿
- [x] #4 命中率/内存/失效指标可观测（供 WebUI/告警）
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 依赖与配置：redis-py（运行时）；序列化按决策（Arrow IPC / pickle+版本头）；FDP_REDIS_URL 注入（compose 已含 Redis 服务）
2. cache 模块：CacheBackend 协议（get/set/delete/incr/锁/统计）+ InMemory + Redis 实现 + Null；LayeredCache（L1→L2）
3. 键与失效：fdh:{domain}:{panel}:{as_of|knowledge_time}:{params_hash}；代际版本号失效（INCR 域代次，免 SCAN）；TTL 按域
4. 防击穿：Redis SET NX PX 跨进程 single-flight（等待+超时回退自算）；fail-open（后端异常视为 miss 并告警一次）
5. 集成：同步成功 → 域代际失效（ingestion on_success 钩子）；readers 提供 cached 包装（供后续 SDK）
6. 观测：命中率/字节/淘汰/锁等待快照（进程内计数 + Redis INFO 内存/淘汰）
7. 测试：键 PIT 规则、分层命中、代际失效、并发 single-flight、fail-open、序列化往返；真 Redis 集成测试
8. 文档：配置手册新增缓存章节；编排 Redis 容量与注入
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
参数定稿（2026-09-13）：单机 2GB 上限 + volatile-lru；纯缓存可关持久化；代际版本号失效；Arrow IPC 序列化（小对象 JSON）；fail-open 直查；观测命中率/内存/淘汰/锁等待。

实现与验证（2026-09-15）：① cache 模块——CacheBackend 协议 + InMemory（TTL/LRU/锁/统计）+ Redis（TTL/INCR/跨进程锁/INFO 指标）+ Null + LayeredCache（L1→L2、fail-open、跨进程 single-flight）；② PIT 安全键（as_of/knowledge_time 互斥必填 + 参数哈希 + 域代际）；③ 代际失效：同步成功 → 域代际 +1（ingestion on_success 钩子）；④ 序列化 Arrow IPC（DataFrame）/JSON（小对象）+ 格式版本；⑤ 集成：bootstrap 按 FDP_REDIS_URL 装配并注入任务；readers.cached_frame 供消费层复用；compose 注入 FDP_REDIS_URL + Redis 2GB/volatile-lru/端口发布；⑥ 依赖：新 extra cache（redis/pyarrow）+ dev fakeredis；Dockerfile extras 已含 cache；⑦ 测试：17 项单测（键/分层/代际/防击穿/fail-open/序列化/工厂）+ 2 项真 Redis 集成；⑧ 文档：配置手册缓存章节、架构横切说明。验证：393 单测 + 14 集成 + ruff/mypy + 链接检查全绿；容器内缓存启用且 Redis ping 通过。

复审修复（8 项）：① stats total 不再重复计 L1；② 代际单调——generation 取 max(L1,L2)，bump 本地推进 + L2 恢复后回写（失败不再静默丢失效）；③ 序列化拒绝不支持类型（不静默 str 化；由 _store 吞掉不缓存）；④ Arrow preserve_index=True（索引往返一致）；⑤ 按域 TTL 真实接线（FDP_CACHE_TTL_<DOMAIN> 经 ttl_resolver）+ 错误变量名修正 + 文档措辞（未配 URL 则缓存全关）；⑥ InMemory incr TTL 语义对齐 Redis；⑦ Redis 端口默认仅本机监听（无鉴权）；⑧ INFO 失败清快照防陈旧。验证：新增 6 项回归测试 → 399 单测 + 14 集成 + ruff/mypy/链接检查全绿；编排重建后缓存启用正常。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
平台共享缓存落地：L1（进程内 TTL/LRU）+ L2（Redis）分层，fail-open 不阻塞数据链路；PIT 安全键（as_of/knowledge_time 互斥必填 + 参数哈希 + 域代际）；同步成功 → 域代际递增失效（免 SCAN）；Redis 锁跨进程 single-flight（超时回退自算）；Arrow IPC/JSON 序列化含格式版本；命中率/字节/淘汰/锁等待可观测。集成：bootstrap 按 FDP_REDIS_URL 装配注入任务、readers.cached_frame 供消费层；compose 注入 + Redis 2GB/volatile-lru/仅本机监听。验证：399 单测（含 6 项评审回归）+ 14 集成（真 Redis 锁/代际/INFO、跨实例防击穿）+ ruff/mypy/链接检查全绿。
<!-- SECTION:FINAL_SUMMARY:END -->
