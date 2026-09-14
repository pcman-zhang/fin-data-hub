---
id: TASK-3.14
title: Entity Registry（实体注册表）落地：标的注册与多源代码映射（原 Security Master）
status: Done
assignee: []
created_date: '2026-09-13 12:16'
updated_date: '2026-09-14 14:23'
labels: []
milestone: m-0
dependencies: []
parent_task_id: TASK-3
ordinal: 50000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
按 doc-10 §3.3 落地平台基石（**终态口径**，含后续 TASK-3.15 收敛）：`entity_id` 主键；`ref.entity`（SCD2：实体身份 / 分类面 / issuer 属性）；`ref.entity_code_history`（canonical 代码履历，旧码可解析）；交易状态不在注册表（由 `cn_equity.listing_lifecycle` 数据集承载，PIT Universe 由其推导）；从 FinDataHub 基础信息（stock/fund/etf/index + delist_list + namechange）构建与刷新；与 TASK-3.2 字典、TASK-3.3 存储联动。

> 本描述按实施终态修订（2026-09-14，实体注册表命名统一）；原始方案（`security_id` / 4 表别名模型）与过程记录见 Implementation Plan / Notes。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 实体模型（EntityRecord/CodeHistoryRecord）+ 仓储协议 + 内存实现；两表 schema（ref.entity SCD2 + ref.entity_code_history，替代别名表）
- [x] #2 entity_id 分配、代码解析（含历史代码 add_code_change）、as-of 宇宙（含退市）与 SCD2 名称/状态还原测试通过
- [x] #3 Hub 构建入口（stock/fund/etf/index + delist_list + namechange）可用；字典条目 ref.entity / ref.entity_code_history 落地
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 领域模型（Security/Alias/Status/Attribute 区间）+ Repository 协议 + InMemory 实现；2. SecurityMaster 服务：security_id 分配、多源别名解析（含有效期）、as-of 宇宙（含退市）、SCD2 名称/状态还原；3. SQLAlchemy Core schema（4 表，迁移执行归 TASK-3.3）；4. Hub 构建入口（stock/fund/etf/index 列表 + delist_list + namechange）；5. 字典条目（ref.security_master/alias/status/attribute）；6. 测试 + 全量检查。

（历史计划，命名与表方案已被后续重构替代；过程见 Notes）
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
实施（2026-09-13）：security_master 模块——领域模型（Security/Alias/Status/Attribute 区间 + BuildStats）、仓储协议 + 内存实现（id 自增，持久化归 3.3）、SecurityMaster 服务（幂等注册、mapper 派生多源别名、as-of 宇宙 list/delist 半开区间、SCD2 名称/状态闭区间还原）、SQLAlchemy Core 四表（ref schema，含唯一/查询索引）、Hub 构建（参考列表 + delist_list + namechange，stats 区分 registered/skipped）。字典新增 ref.security_master / ref.security_alias（Domain.REF）。测试 8 项；全量 299 passed；ruff/mypy clean。延期：DDL 生成/迁移执行与持久化仓储 → TASK-3.3。

评审修复（2026-09-13）：① 增量刷新（已注册标的的退市/状态/名称变化更新记录并补写状态区间，BuildStats 增加 updated）；② 别名 valid_from 兜底 _EPOCH（防 NaT 主键）；③ name/status_as_of 防前视（有区间未覆盖返回 None）；④ 别名计数 O(1)（仓储计数）；⑤ add_status/add_attribute 起始日非法显式报错。

重构（2026-09-13，设计确认）：security_id → entity_id；4 表收敛为 2 表（ref.entity SCD2 合并 status/attribute；ref.entity_code_history 替代多源别名表——证券源代码由 Hub mapper 归一、序列映射归字典）；包重命名 security_master → registry（EntityRegistry）。doc-10 §3.3 冻结稿修订；doc-17/19 重新生成。

代码评审修复（2026-09-13）：① 名称刷新失效（版本冲突）→ 版本号改为实体级单调 _next_version；② _current_row 优先 open 区间（当前行不再返回过期临时名称行）；③ add_name_change 改为完整 SCD2（闭合前段 + 临时区间 + 恢复行），消除"旧开区间复活"歧义；④ 退市路径保留同批新名称；⑤ BuildStats 改为 created/updated/skipped 互斥口径；⑥ 文案同步（引用注册表）。新增回归测试 3 项。
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-09-14 14:23
---
术语统一（2026-09-14）：标题与描述按 Entity Registry（实体注册表）终态修订；原始 Security Master 命名、4 表方案与过程记录保留于 Plan/Notes。代码侧同步：registry 各模块 docstring、dictionary/ref/entity.yaml、daily_bar.yaml 字段描述；doc-2/10/11/12/13/14/17/19 同步清扫；doc-17/19 已按字典重新生成。
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
引用注册表落地：entity_id 身份 + SCD2 属性/生命周期 + 代码履历（旧码可解析）；两表 schema 与字典条目；Hub 构建（含增量退市刷新）；全量 tests/ruff/mypy 全绿。
<!-- SECTION:FINAL_SUMMARY:END -->
