---
id: TASK-3.1
title: 平台架构设计：FinDataPlatform / DataPanel(PIT) / 存储 / 部署 / WebUI
status: In Progress
assignee: []
created_date: '2026-09-13 05:59'
updated_date: '2026-09-13 12:11'
labels: []
milestone: m-0
dependencies: []
parent_task_id: TASK-3
ordinal: 20000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
输出 v1 平台设计文档：**SDK 优先**——FinDataPlatform Python SDK（直连只读副本/读模型，原生 PIT/as-of 参数与元数据），REST/WebUI/批量导出为其薄封装；**凭证与权限模型（三面：内部写入 / SDK 只读 DB 角色 / REST API Key 作用域 read/export/admin，不提供数据写入）**；内部 DataPanel 数据平面（数据域、PIT 双时间轴：事件时间+知识时间、as-of 查询与重述策略、口径与血缘）；DataSource/Adapter 插件化扩展（复用 v0 capability/限流/计量，含 BaoStock 等候选）；PostgreSQL + TimescaleDB 存储模型；Redis L2 共享缓存（L1 内存 + L2 Redis、PIT 安全键、失效与防击穿）；DuckDB 分析/加工引擎定位（Parquet ETL、派生计算、质量扫描，非缓存非真源）；只读副本 + 稳定读模型（mart/api schema 视图，PIT 安全）与权限审计；采集调度（已定：APScheduler + PG job store）与部署拓扑（compose/K8s）；管理型 WebUI 信息架构；目录结构 platform/{fin_data_platform, services/{api,scheduler,webui}, docker}（见 doc-2 §6）。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 设计文档评审通过；明确首批数据域与优先级
- [ ] #2 数据字典 schema 与派生指标表达规范定稿（可机读）
- [ ] #3 部署拓扑与配置/凭证注入方案定稿（不落镜像）
- [ ] #4 输出任务拆分与里程碑排期
- [ ] #5 设计文档评审通过；首批数据域与优先级明确
- [ ] #6 FinDataPlatform REST 契约与 PIT（as-of）语义定稿
- [ ] #7 DataSource/Adapter 扩展接口与目录结构定稿（platform/ 方案）
- [ ] #8 TimescaleDB schema 策略（hypertable/连续聚合/压缩保留）与部署拓扑定稿
- [ ] #9 管理 WebUI 信息架构与权限模型定稿；输出任务拆分与排期
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
第一章架构总纲（分层/依赖规则/根本要求）→ 数据字典规范 → REST 契约 → TimescaleDB schema → WebUI IA → 整合评审。以分支 feat/v1-data-platform 小粒度提交，便于 review。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
范围决策（2026-09-13）：① 数据域以 Fuyao 平台能力范围为准 + 保留宏观数据平面；② 单机 Docker（compose），不需要 K8s；③ 历史回填由用户提供数据文件，平台提供 Parquet/CSV 幂等导入通道；④ 下游系统暂不在本期考虑；⑤ 权益市场平面：创业板属 A 股板块（非独立市场），建议同一权益平面内以 market/exchange/board 维度区分，H股/美股为后续扩展。

PIT 定稿（2026-09-13）：行情/快照天然 PIT；公司行为/复权因子版本化（复权价按 as-of 计算）；财务/宏观 append-only 版本（as-first-reported/restated）；成分 SCD2 + 生效区间；公告 knowledge=发布时间；标准字段 event_date/knowledge_date/ingest_ts/version/is_latest/source（见 doc-2 §6.9）。

目录/分层定稿（2026-09-13）：src/fin_data_hub（① FinDataHub 多源接入，唯一数据源访问平面）→ src/fin_data_platform（② SDK）→ services/api（③ 薄 REST）→ services/webui（④ 基于 REST）；scheduler 复用 ①②；docker/ 单机 compose。禁止反向依赖/跨层直连（doc-2 §6.10）。

市场平面定稿（2026-09-13）：统一平台、市场分平面——cn_equity/cn_fund/cn_futures/cn_options/hk_equity/us_equity/us_options 各自 Normalization；共享 Security Master/PIT/字典/质量/存储/SDK；宏观单一平面（含汇率官方序列；TLT/SHY 按数据形态归属）；HK/US 代码模型扩展纳入设计（doc-2 §6.11）。Redis 2G/volatile-lru/代际失效/Arrow/fail-open；只读副本暂不做、保留读写 DSN 分离。

指数子平面与归一化层（2026-09-13）：指数分 cn_index/hk_index/us_index(.GI)/ths_index(.TI)/wind_index(.WI)；canonical 遵循 Wind 标准，不支持者映射校准；归一化层在 fin_data_hub（请求代码/参数转换 + 响应归一化，spec 驱动），platform 做面板级归一化（doc-2 §6.12）。

存储读写模块方案见 doc-2 §6.13（engine/schema/migrations/writers/readers/versioning；读写 DSN 分离；幂等+PIT append-only；as-of 读模型；Arrow；SQLAlchemy Core+Alembic+psycopg3）。

修正（2026-09-13）：写入面=平台内部写入端（ingestion/派生计算/文件导入/质量结果），按 schema 最小授权；派生数据需血缘与重述重算（TASK-3.12）。

时序定稿（2026-09-13）：数据平面=双时间轴时序（event_time × knowledge_time）；能力清单与 SDK 草图见 doc-2 §6.14；TASK-3.13 落地。

未来特性（2026-09-13，暂不开发）：高频数据透传不入库（归一化后直接返回，绕过缓存/PIT），延迟统计输出 p99/mean（复用 UsageLedger latency 扩展分位数）——见 doc-2 §6.15；设计时预留透传路径接口。

接口模型决策：v1 SDK/REST 使用 Pydantic v2（请求/响应/配置/元数据模型），REST 复用同一模型生成 OpenAPI；v0 hub 不引入 Pydantic（doc-2 §6.17）。

第一章完成（2026-09-13，doc-10）：三层结构（接入/数据/服务）、控制面与数据面拆分、缓存横切、依赖硬约束、根本要求（准确/新鲜 SLA 可度量/PIT 三要素）、补充要求（可审计、可扩展、成本权限、compose 部署）与任务落位映射。待评审。

第 2 稿（2026-09-13，采纳评审）：新增 §3.1 DataPanel=逻辑数据集、§3.2 Raw→Canonical→Read Model（SDK/REST 只读 Read Model）、§3.3 Security Master（与 PIT 同级，security_id + 多源别名 + SCD2）、§3.4 Cache 非权威、§4.1 四时间模型（event/publish/knowledge/ingest）、§6.1 Schema First（Dictionary→Schema→SDK/API）。doc-2 §6.9 标准字段同步为四时间命名。待确认：Security Master 是否新增 TASK-3.14。
<!-- SECTION:NOTES:END -->
