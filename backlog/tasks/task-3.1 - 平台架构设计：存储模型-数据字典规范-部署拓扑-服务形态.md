---
id: TASK-3.1
title: 平台架构设计：FinDataPlatform / DataPanel(PIT) / 存储 / 部署 / WebUI
status: Done
assignee: []
created_date: '2026-09-13 05:59'
updated_date: '2026-09-13 12:56'
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
- [x] #1 架构总纲定稿：三层结构/概念（DataPanel=逻辑数据集、Raw→Canonical→Read Model、Security Master、Cache 非权威）/四时间模型/Schema First（doc-10，已冻结）
- [x] #2 数据字典规范定稿：机读 meta-schema、CI 校验、语义版本、代码化派生算法登记、变更流程（doc-11，已冻结）
- [x] #3 REST 契约与 PIT（as-of）语义定稿：version_mode 三模式、publish strict/allow、结构化 filters、代次与 ETag、Cost Header（doc-12，已冻结）
- [x] #4 TimescaleDB schema 策略定稿：域 schema、partition_strategy、is_latest 读侧派生、无 FK、压缩与 PIT 一致性门禁、投影表代次（doc-13，已冻结）
- [x] #5 部署拓扑与凭证注入定稿：单机 compose、凭证三面（内部写入/只读角色/API Key）不落镜像（doc-2 §6.8、doc-10 §6.4、doc-12 §6）
- [x] #6 WebUI IA 设计完成（doc-14，低优先级暂不冻结；认证授权/通知渠道移至 doc-15/doc-16 暂不制作）；任务拆分与里程碑就绪（m-0，TASK-3.1~3.14）
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

第 3 稿（2026-09-13，采纳评审）：Read Model 语义版本化（字段兼容≠语义兼容，加字段不升版、口径变化升版）；宏观分域 macro_cn/macro_us/macro_global（防垃圾桶）；新增 §6.2 Source Independence Principle（canonical/read model 禁供应商特有字段，provider 维度 + Raw 层例外 + CI 校验）。doc-2 §6.11 同步宏观分域。

数据字典规范第 1 稿（2026-09-13，doc-11）：YAML + Pydantic 元 schema；dataset/field 两级结构（含 SLA/coverage/quality/lineage/derived/source_mappings）；安全公式子集；CI 强制校验（provider 无关/语义版本/一致性）；生成物映射与变更流程；待评审：格式（YAML vs TOML）、文件粒度、公式 DSL 边界、派生登记范围。TASK-3.14 Security Master 已建。

数据字典规范第 2 稿（2026-09-13，采纳 8 项评审）：semantic_version 整数；decimal precision/scale；business_key/physical_key 拆分；quality 跨字段 expression 规则；mappings 移至 dataset 级（Schema/Adapter 分离）；coverage 可计算（universe_source + expected_dates）；lineage 强制；公式不入字典（derived 仅 inputs/output/owner，公式归 TASK-3.12 引擎）。

REST 契约第 1 稿（2026-09-13，doc-12）：只读薄封装；dataset-generic 路由 + SDK↔REST 映射；as_of/as_of_policy(knowledge|publish)/include_history/include_meta；复权 factor_ref 与 algorithm_id 回溯；游标分页/Arrow/ETag；RFC9457 错误模型；API Key scopes+审计+限流+PIT 安全缓存；待决策：路由风格、是否开放 POST query、include_meta 默认、publish 回退策略。

REST 契约第 2 稿（2026-09-13，采纳评审）：删除 /latest（统一 rows + version_mode latest/as_of/history，as_of 必填不隐式 now）；publish fallback 显式 strict(默认 422)/allow；filters 结构化 AST；cursor=order_by+业务键+物理键；ETag 含 read_model_version+data_generation；派生 algorithm_id 始终返回；X-Query-Cost/Cache 头；研究快照端点预留。§10 决策记录 8 条。

REST 契约冻结（2026-09-13，doc-12 第 3 稿）：version_mode 必选枚举（缺失 422 version_mode_required）；X-Data-Generation（Read Model 构建代次 YYYYMMDDTHHMMSSZ）纳入响应头/ETag/审计/缓存/排障。doc-12 已冻结。

TimescaleDB schema 第 2 稿（2026-09-13，采纳评审）：partition_strategy 显式（market→event_time、versioned→knowledge_time 默认推导）；Canonical 不存 is_latest（读侧派生）；默认不建 FK；Read Model 三实现显式（view 默认/projection_table/首期不用 MV）。doc-11 冻结稿同步修订 storage 字段；doc-10 §4.2 注明 is_latest 读侧派生。

压缩与 PIT 规范（2026-09-13，doc-13 §3.4）：压缩不得改变查询语义；仅压缩已封口 chunk；禁依赖 segmentby/orderby 语义；三模式压缩前后逐行一致 CI 门禁（样本/边界/失败阻断）；压缩参数登记字典 storage.compression（doc-11 同步修订）。

WebUI IA 第 1 稿（2026-09-13，doc-14）：管理型控制台（REST 单一数据面，不直连 DB）；11 个一级导航（总览/数据域/同步任务/质量/新鲜度/血缘/派生算法/Security Master/快照导出/系统治理/个人）；角色 viewer/operator/admin + 操作矩阵 + 审计；待决策 5 项。

WebUI IA 第 2 稿（2026-09-13）：按个人平台定位收敛——认证/授权/SSO 移至 doc-15（暂不制作）；WebUI 首期本机访问无账号；保留二次确认与最小事件日志。

收口（2026-09-13）：设计文档集——doc-10 架构总纲（冻结）、doc-11 数据字典（冻结）、doc-12 REST 契约与 PIT（冻结）、doc-13 TimescaleDB 策略（冻结）、doc-14 WebUI IA（低优先级暂不冻结，接口稳定后再定稿）、doc-15 认证授权（暂不制作）、doc-16 通知渠道（暂不制作）。决策：个人平台定位，认证/授权/通知后置；事件日志不保留。任务拆分：m-0（TASK-3.1~3.14，Security Master 已纳入）。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
TASK-3.1 设计收口：5 份定稿物完成（总纲/字典/REST/存储冻结；WebUI IA 低优先级暂缓），增强项（认证授权/通知）独立文档并标记暂不制作；任务拆分与里程碑 m-0（3.1~3.14）就绪。
<!-- SECTION:FINAL_SUMMARY:END -->
