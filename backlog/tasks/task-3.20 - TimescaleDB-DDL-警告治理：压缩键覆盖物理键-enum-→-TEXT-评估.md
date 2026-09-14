---
id: TASK-3.20
title: TimescaleDB DDL 警告治理：压缩键覆盖物理键 + enum → TEXT 评估
status: To Do
assignee: []
created_date: '2026-09-14 15:29'
labels: []
milestone: m-0
dependencies: []
parent_task_id: TASK-3
ordinal: 59000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
背景（TASK-3.4 容器化实测发现）：`docker compose up` 迁移日志出现两类 TimescaleDB 建议性 WARNING——

1. **压缩键未覆盖物理键**：压缩配置 `segment_by=entity_id, order_by=trade_date`，而物理键为 `(entity_id, trade_date, knowledge_time, version)`；TimescaleDB 提示 `knowledge_time` / `version` 应参与 segmenting/ordering。影响：压缩块中的唯一索引不强制执行（当前写入落未压缩块，风险低，但建议对齐）。
2. **`character varying` 建议改 `TEXT`**：字典 `enum` 类型映射为 `String(32)`（如 provider / report_type）；PostgreSQL 中两者性能相同，属建议。

目标：消除告警并保持 PIT/幂等语义不变。

方案要点：
- 压缩 orderby 覆盖物理键（如 `order_by: trade_date, knowledge_time, version`），字典 + 基线重生成 + 新增迁移修订（升级库 ALTER 压缩设置）；
- enum 映射评估：改 `TEXT`（字典 CI 仍校验枚举值）或保留 `String(32)` 并记录理由；
- 漂移测试（基线生成一致性）、升级/回滚验证、容器迁移日志无告警。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 压缩配置覆盖物理键（knowledge_time/version）；新库与升级库均生效（新增修订）；迁移日志无 segment/order 告警
- [ ] #2 enum 类型映射处置明确：改 TEXT（含基线重生成与修订）或保留并文档记录理由
- [ ] #3 验证：基线漂移测试、升级/回滚、容器迁移日志干净；pytest / ruff / mypy 全绿
<!-- AC:END -->
