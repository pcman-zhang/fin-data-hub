---
id: TASK-2.18
title: 归一化层：Wind 标准代码映射 + 请求参数转换 + 响应归一化（spec 驱动）
status: To Do
assignee: []
created_date: '2026-09-13 08:41'
labels: []
dependencies:
  - TASK-2.2
parent_task_id: TASK-2
ordinal: 32000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
按 doc-2 §6.12 落地源侧归一化层：canonical 遵循 Wind 标准并扩展 venue（.O/.N/.A/.GI/.TI/.WI/.CSI）与指数类型；各源 CodeMap 覆盖 HK/US/指数/自定义指数（不支持者用映射校准）；请求参数转换（日期/复权/市场后缀/endpoint 参数形态）；响应归一化（字段/单位/枚举/时区/币种/日期 → hub 统一 schema）；映射 spec 机读（source × endpoint）并与平台数据字典一致；边界：hub 做源级归一化，platform 做面板级。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 SecCode/SecType 支持 Wind 标准 venue（含 .O/.N/.A/.GI/.TI/.WI）与指数类型；映射往返测试通过
- [ ] #2 各源 CodeMap 覆盖 HK/US/指数/自定义指数；不支持场景有明确映射或可诊断报错
- [ ] #3 请求参数转换与响应归一化 spec 化（机读文件）+ 覆盖度校验
- [ ] #4 与平台数据字典一致性校验（CI）；全量测试通过
<!-- AC:END -->
