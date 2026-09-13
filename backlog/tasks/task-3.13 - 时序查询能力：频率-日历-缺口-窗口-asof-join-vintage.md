---
id: TASK-3.13
title: 时序查询能力：频率 / 日历 / 缺口 / 窗口 / asof join / vintage
status: To Do
assignee: []
created_date: '2026-09-13 08:56'
updated_date: '2026-09-13 08:59'
labels: []
milestone: m-0
dependencies:
  - TASK-3.1
  - TASK-3.3
parent_task_id: TASK-3
ordinal: 34000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
在数据平面/SDK 落地双时间轴时序能力：范围序列查询（多键×字段×频率）、日历/时区/会话、重采样与连续聚合、缺口策略（null/前值/最近值）、窗口与滚动（PIT 正确）、跨序列对齐与 asof join、vintage/版本历史查询、多频段（日频+分钟级）。存储侧用 TimescaleDB 连续聚合/time_bucket_gapfill/按频分级压缩保留支撑。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 get_series/get_cross_section/get_versions/get_panel 语义落地（含 freq/as_of/fill/calendar 参数）
- [ ] #2 日历/时区/会话与缺口策略有明确规范与测试
- [ ] #3 重采样/连续聚合与窗口计算 PIT 正确（只用 as_of 可见数据）
- [ ] #4 vintage 序列与版本历史可查；多频段（日频/分钟级）路径可用
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
范围说明：本期只做入库时序（双时间轴）；高频透传与延迟统计为未来特性（doc-2 §6.15，暂不开发）。
<!-- SECTION:NOTES:END -->
