---
id: TASK-3.14
title: Security Master 落地：标的注册与多源代码映射
status: Done
assignee: []
created_date: '2026-09-13 12:16'
updated_date: '2026-09-13 13:22'
labels: []
milestone: m-0
dependencies: []
parent_task_id: TASK-3
ordinal: 50000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
按 doc-10 §3.3 落地平台基石：security_id 主键；security_alias（多源代码 + 有效期）；security_status_history（上市/暂停/退市）；security_attribute_history（名称/ST/类型 SCD2）；含退市永久保留；as-of 宇宙查询；DataPanel 强制挂载 security_id；从 FinDataHub 基础信息（stock/fund/etf/index + delist_list + namechange）构建与刷新；与 TASK-3.2 字典、TASK-3.3 存储联动。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Security Master 领域模型 + 仓储协议 + 内存实现；四张逻辑表 SQLAlchemy Core schema 定义落地（DDL/迁移执行随 TASK-3.3）
- [x] #2 security_id 分配与多源代码别名解析（含有效期）可用；as-of 宇宙（含退市）与 SCD2 名称/状态还原测试通过
- [x] #3 Hub 构建入口（stock/fund/etf/index 列表 + delist_list + namechange）可用；字典条目 ref.security_master / ref.security_alias 落地
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 领域模型（Security/Alias/Status/Attribute 区间）+ Repository 协议 + InMemory 实现；2. SecurityMaster 服务：security_id 分配、多源别名解析（含有效期）、as-of 宇宙（含退市）、SCD2 名称/状态还原；3. SQLAlchemy Core schema（4 表，迁移执行归 TASK-3.3）；4. Hub 构建入口（stock/fund/etf/index 列表 + delist_list + namechange）；5. 字典条目（ref.security_master/alias/status/attribute）；6. 测试 + 全量检查。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
实施（2026-09-13）：security_master 模块——领域模型（Security/Alias/Status/Attribute 区间 + BuildStats）、仓储协议 + 内存实现（id 自增，持久化归 3.3）、SecurityMaster 服务（幂等注册、mapper 派生多源别名、as-of 宇宙 list/delist 半开区间、SCD2 名称/状态闭区间还原）、SQLAlchemy Core 四表（ref schema，含唯一/查询索引）、Hub 构建（参考列表 + delist_list + namechange，stats 区分 registered/skipped）。字典新增 ref.security_master / ref.security_alias（Domain.REF）。测试 8 项；全量 299 passed；ruff/mypy clean。延期：DDL 生成/迁移执行与持久化仓储 → TASK-3.3。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Security Master 核心落地：多源别名解析（canonical/tushare/baostock/akshare）、as-of 宇宙（含退市半开区间）、SCD2 名称/状态还原、Hub 构建入口；四表 SQLAlchemy schema 定义 + 字典条目；299 tests/ruff/mypy 全绿（迁移执行随 TASK-3.3）。
<!-- SECTION:FINAL_SUMMARY:END -->
