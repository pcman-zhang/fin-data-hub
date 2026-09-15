---
id: TASK-3.20
title: TimescaleDB DDL 警告治理：压缩键覆盖物理键 + enum → TEXT 评估
status: Done
assignee:
  - '@freeman'
created_date: '2026-09-14 15:29'
updated_date: '2026-09-15 13:30'
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
- [x] #1 压缩配置覆盖物理键（knowledge_time/version）；新库与升级库均生效（新增修订）；迁移日志无 segment/order 告警
- [x] #2 enum 类型映射处置明确：改 TEXT（含基线重生成与修订）或保留并文档记录理由
- [x] #3 验证：基线漂移测试、升级/回滚、容器迁移日志干净；pytest / ruff / mypy 全绿
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. enum 映射 String(32) → Text（文档串同步；枚举校验由字典 CI 承担）
2. 压缩配置覆盖物理键：5 个数据集的 order_by 追加 knowledge_time/version（segment_by 覆盖其余键）
3. 基线重生成（write_baseline）；新增修订 0003：存量库 varchar→text + 重设压缩键（含已压缩 chunk 处理）
4. 测试：漂移校验、压缩语句断言、VARCHAR 断言更新
5. 验证：全新库迁移日志无告警；升级库（存量）迁移通过；pytest/ruff/mypy
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
实现与验证（2026-09-14）：① enum→Text（storage/schema.py），基线重生成（13 处 VARCHAR(32)→TEXT，含 ref 表——字典条目优先）；② 5 个数据集压缩 order_by 覆盖物理键；③ 新增修订 0003_ddl_hygiene（解压 → 删读模型 → varchar→text → 重建读模型 → 重设压缩键；降级恢复旧压缩键、类型不回退）；④ 新增字典/压缩不变量测试与 0003 漂移测试。实测：存量库 0002→0003（head=0003、无 varchar 残留、5 表压缩键覆盖物理键）；全新库 0001→0003 迁移日志 WARNING=0；集成迁移测试（升级/降级/重复）通过。⑤ 发现并修复：ref.entity 列被 mart 视图依赖导致类型变更被拒——0003 改为先删读模型再重建。文档：doc-13 增补压缩键覆盖与枚举 text 规则。验证：376 单测 + ruff/mypy 全绿。遗留：容器镜像重建受 Docker Hub 不可达阻塞（Docker Desktop 无代理），待网络恢复后复验容器迁移日志。

容器复验完成（2026-09-15）：镜像重建（本地基础镜像导入 + 离线 wheels 构建）后——① 容器内全新库迁移 0001→0003，日志 WARNING=0；② 栈三服务 healthy，容器内 --check 退出 0；③ 存量库升级路径（0002→0003）此前已通过。说明：Docker Desktop 代理已配置（HTTP/HTTPS 均指向 host.docker.internal:7897），但宿主代理仅监听 127.0.0.1，Docker VM 无法直连；本次通过「WSL 侧拉取基础镜像 + 离线 wheels」完成镜像重建验证，仓库 Dockerfile 未改动（正常网络环境按原方式构建）。最终：376 单测 + ruff/mypy + 链接检查全绿。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
TimescaleDB DDL 告警治理完成：① 压缩键覆盖物理键——5 个数据集 order_by 追加 knowledge_time/version（segment_by 覆盖其余键），新增 CI 不变量测试，压缩块唯一性约束恢复；② enum 类型映射 String(32)→Text，基线重生成（13 处，含 ref），新增修订 0003_ddl_hygiene 覆盖存量库（解压 → 删读模型 → varchar→text → 重建读模型 → 重设压缩键；降级恢复旧压缩键、类型不回退）；③ 顺带修复「ref.entity 列被 mart 视图依赖导致类型变更被拒」。验证：存量库升级与容器内全新库迁移日志 WARNING=0、集成升级/降级测试通过、376 单测 + ruff/mypy 全绿；doc-13 补充压缩键与类型规则。
<!-- SECTION:FINAL_SUMMARY:END -->
