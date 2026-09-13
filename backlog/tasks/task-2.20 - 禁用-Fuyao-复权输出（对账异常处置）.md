---
id: TASK-2.20
title: 禁用 Fuyao 复权输出（对账异常处置）
status: Done
assignee: []
created_date: '2026-09-13 09:54'
updated_date: '2026-09-13 09:56'
labels: []
dependencies:
  - TASK-2.16
parent_task_id: TASK-2
ordinal: 36000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
按 doc-4 调查结论：Fuyao 预计算复权序列异常（日收益衰减 0.844×、同日 OHLC 比值不一致）。v0 处置：FuyaoAdapter 仅支持 adjust=None（原始价）；adjust=qfq/hfq 抛 UnsupportedCapability 并提示改用 Tushare/Wind 或原始价 + 因子。文档同步（README/doc-3/doc-2）。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 FuyaoAdapter 拒绝 qfq/hfq（UnsupportedCapability + 明确提示）；adjust=None 正常
- [x] #2 测试更新：复权拒绝用例 + 原始价路径回归
- [x] #3 README/doc-3/doc-2 记录处置与原因（引用 doc-4）
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. fuyao.py 移除复权映射并拒绝 qfq/hfq；2. 测试更新；3. README/doc-3/doc-2 同步；4. pytest/ruff/mypy 验证并收尾。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
验证：全库 187 passed；ruff/mypy 全过。实现：fuyao.py 移除复权映射，adjust≠None 抛 UnsupportedCapability（提示 Tushare/Wind 或 raw+factor）；测试改为拒绝用例；README/doc-3/doc-2 同步并引用 doc-4。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
完成 Fuyao 复权异常处置：v0 禁用 Fuyao 复权输出（仅 adjust=None），复权统一走原始价 + 因子；文档同步调查结论。验证：187 项单测通过，ruff/mypy 干净。
<!-- SECTION:FINAL_SUMMARY:END -->
