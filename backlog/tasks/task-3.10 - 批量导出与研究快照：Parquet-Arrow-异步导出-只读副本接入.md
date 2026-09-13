---
id: TASK-3.10
title: 批量导出与研究快照 + 只读副本/读模型（对外量化通道）
status: To Do
assignee: []
created_date: '2026-09-13 06:21'
updated_date: '2026-09-13 08:34'
labels: []
milestone: m-0
dependencies:
  - TASK-3.3
parent_task_id: TASK-3
ordinal: 29000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
面向外部量化消费的批量与直连通道：① 按域/标的/时间窗异步导出 Parquet/Arrow（对象存储或共享卷 + 下载链接），供回测与研究；② 只读副本 + 稳定读模型（mart/api schema 视图、PIT/as-of 安全、版本化与弃用流程）；③ 按域只读角色与审计、资源隔离（statement_timeout/连接数）；④ 可选 ADBC/Arrow SQL。禁止外部直连内部原始表。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 异步导出可用：任务提交/状态/下载全流程，产物为 Parquet/Arrow
- [ ] #2 全市场长历史导出不经过在线 REST 查询通道（避免逐标的拉取）
- [ ] #3 稳定读模型（PIT/as-of 视图、版本化、数据字典登记）与按域只读角色/审计落地
- [ ] #4 外部不直连内部原始表；资源隔离生效
- [ ] #5 只读副本暂不考虑（非商业部署）；保留读写 DSN 分离配置供未来拆分
<!-- AC:END -->
