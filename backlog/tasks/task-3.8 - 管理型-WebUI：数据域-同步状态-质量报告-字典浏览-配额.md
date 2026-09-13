---
id: TASK-3.8
title: 管理型 WebUI：数据域 / 同步状态 / 质量报告 / 字典浏览 / 配额
status: To Do
assignee: []
created_date: '2026-09-13 06:07'
updated_date: '2026-09-13 12:54'
labels: []
milestone: m-0
dependencies:
  - TASK-3.1
  - TASK-3.3
  - TASK-3.7
parent_task_id: TASK-3
ordinal: 27000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
管理控制台：数据域与同步状态总览、数据质量报告、数据字典与血缘浏览、调度任务管理、配额/成本看板；权限模型按设计（只读/运维角色）。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 WebUI 覆盖设计定稿的信息架构（域/同步/质量/字典/任务/配额）
- [ ] #2 权限与审计接入平台鉴权体系
- [ ] #3 随 docker compose 一键部署可用
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
范围收敛（2026-09-13，个人平台定位）：认证/授权/SSO 属于生产级能力，分离至 doc-15《认证与授权（增强功能，暂不制作）》；首期 WebUI 仅本机 127.0.0.1、无账号体系；保留高风险操作二次确认与最小事件日志。

决策（2026-09-13）：事件日志不保留（个人平台首期）；通知渠道独立为 doc-16（飞书等，暂不制作）。
<!-- SECTION:NOTES:END -->
