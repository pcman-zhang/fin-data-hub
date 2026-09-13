---
id: doc-11
title: 数据字典规范（可机读）
type: specification
created_date: '2026-09-13 12:16'
updated_date: '2026-09-13 12:16'
---
# 数据字典规范（可机读）

> 状态：评审中（第 1 稿） | 关联：doc-10（架构总纲 §6.1 Schema First）、TASK-3.1/3.2、TASK-3.14
> 定位：数据字典是平台的**唯一事实源**（Single Source of Truth）；DDL、归一化映射、SDK/REST 模型、WebUI 字典、质量规则**均由字典生成或经 CI 强校验一致**。

## 1. 原则

1. **Schema First**：Dictionary → Schema → SDK/API；禁止"代码先写、文档后补"；
2. **覆盖完整**：每个 DataPanel 必须登记——字段/类型/单位/PIT 类别/约束/血缘/派生公式/覆盖率/SLA/存储映射/质量规则；
3. **Provider 无关**（doc-10 §6.2）：canonical 字段不得含供应商品牌/缩写；源差异放 Raw 层或 `source_mappings`（仅登记，不进入公共 schema）；
4. **语义版本**（doc-10 §3.2）：字典条目带 `version`；字段含义/口径变化升主版本，纯增量不升；
5. **机读优先**：一律可被程序解析、校验、生成；人读文档由字典渲染。

## 2. 文件形态与目录

- 格式：**YAML**（可注释、层级友好）；加载后用 **Pydantic v2** 严格校验（v1 平台已采用 Pydantic）；
- 目录：`platform/dictionary/<domain>.yaml`（每数据域一文件，条目按 dataset 排列；diff 可 review）；
- 元 schema：`platform/dictionary/_schema/dictionary.schema.json`（由 Pydantic 模型导出，CI 双向校验）；
- 命名：
  - `dataset`：`{domain}.{dataset}`，小写蛇形（如 `cn_equity.daily_bar`）；
  - 字段：小写蛇形；禁止源前缀（`wind_*`/`ts_*`），来源维度用 `provider`；
  - 派生数据集：`{domain}.{name}_derived` 或以血缘标注区分。

## 3. 条目结构（meta-schema）

### 3.1 dataset 级

| 键 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `dataset` | str | ✅ | `{domain}.{dataset}`，全局唯一 |
| `version` | str | ✅ | 语义版本（`1.0` / `1.1` / `2.0`） |
| `domain` | enum | ✅ | doc-10 §3.1 的 DataDomain |
| `description` | str | ✅ | 口径、用途、注意事项 |
| `pit_class` | enum | ✅ | `market` / `versioned` / `scd2` / `snapshot` |
| `primary_key` | [str] | ✅ | 业务主键（含 `security_id`） |
| `grain` | str | ✅ | 粒度描述（如 "标的 × 交易日"） |
| `update_sla` | obj | ✅ | `{frequency, earliest_available, latest_available, tolerance}`（doc-10 §5.2） |
| `sources` | [obj] | ✅ | `[{provider, endpoint, note?}]`（采集入口） |
| `coverage` | obj | ✅ | `{universe, history_start, note?}`（宇宙含退市，引用 Security Master） |
| `storage` | obj | ✅ | `{canonical_table, read_model, partition_by, retention}` |
| `quality` | [obj] | ✅ | `[{rule, params..., severity}]`；rule ∈ unique/not_null/range/enum/reconcile/freshness/custom |
| `lineage` | obj | | `{upstream:[{dataset, fields?}], transform}`（派生/加工必填） |
| `derived` | obj | | `{formula, inputs:[dataset.field], asof}`（派生数据集必填；见 §4） |
| `fields` | [obj] | ✅ | 字段列表（§3.2） |

### 3.2 field 级

| 键 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | str | ✅ | canonical 字段名（provider 无关） |
| `type` | enum | ✅ | `int64 / float64 / decimal / string / bool / date / timestamp / timestamp_tz / enum` |
| `unit` | str? | | 单位（元/股/%/点…）；百分比数值需注明"百分数" |
| `nullable` | bool | ✅ | 是否可空 |
| `enum` | [str] | | type=enum 时必填 |
| `range` | obj | | `{min, max}`（数值/日期） |
| `description` | str | ✅ | 含义与口径 |
| `pit_role` | enum | ✅ | `event_time / publish_time / knowledge_time / ingest_time / none` |
| `source_mappings` | [obj] | | `[{provider, field, transform?}]`（登记源字段映射；不进入公共 schema） |

## 4. 派生公式表达（安全子集）

- 引用语法：`dataset.field`（如 `cn_equity.daily_bar.close`）；
- 运算符/函数（白名单）：`+ - * /`、`sum/mean/min/max/std`、`lag/diff/pct_change`、`rank/where/coalesce`、窗口 `over (partition by … order by …)`；
- `asof`：`knowledge_time`（默认）——所有输入按 `knowledge_time <= as_of` 取版本；
- 禁止：外部 IO、随机数、未登记函数、跨域隐式 join；
- CI：公式可解析 + 输入全部存在 + 血缘无环 + as-of 语义标注完整。

**示例**（前复权，as-of 计算，不落快照）：

```yaml
derived:
  qfq_close:
    formula: "close * adj_factor / last(adj_factor) over (partition by security_id order by trade_date)"
    inputs: [cn_equity.daily_bar.close, cn_equity.adj_factor.adj_factor]
    asof: knowledge_time
```

## 5. 完整示例：`cn_equity.daily_bar`

```yaml
dataset: cn_equity.daily_bar
version: "1.0"
domain: cn_equity
description: A 股日线行情（不复权原始价；复权价按 raw + factor、as-of 计算）
pit_class: market
primary_key: [security_id, trade_date]
grain: 标的 × 交易日
update_sla:
  frequency: daily
  earliest_available: "T+0 18:00"
  latest_available: "T+0 22:00"
  tolerance: "2h"
sources:
  - provider: tushare
    endpoint: daily
  - provider: baostock
    endpoint: query_history_k_data_plus
coverage:
  universe: A 股（含退市；见 cn_equity.security_master）
  history_start: 1990-12-19
storage:
  canonical_table: cn_equity.daily_bar
  read_model: mart.equity_daily_bar_v1
  partition_by: trade_date(月)
  retention: all
quality:
  - rule: unique
    keys: [security_id, trade_date]
  - rule: range
    field: volume
    min: 0
  - rule: reconcile
    against: raw_stock_daily
fields:
  - name: security_id
    type: int64
    nullable: false
    description: 平台标的 ID（Security Master 主键）
    pit_role: none
  - name: trade_date
    type: date
    nullable: false
    description: 交易日
    pit_role: event_time
  - name: open
    type: float64
    unit: 元
    nullable: true
    description: 开盘价（不复权）
    pit_role: none
  - name: close
    type: float64
    unit: 元
    nullable: true
    description: 收盘价（不复权）
    pit_role: none
  - name: volume
    type: float64
    unit: 股
    nullable: true
    description: 成交量
    pit_role: none
  - name: amount
    type: float64
    unit: 元
    nullable: true
    description: 成交额
    pit_role: none
  - name: knowledge_time
    type: timestamp_tz
    nullable: false
    description: 该版本进入平台的时间
    pit_role: knowledge_time
  - name: publish_time
    type: timestamp_tz
    nullable: true
    description: 行情发布/可得时间（若源提供）
    pit_role: publish_time
  - name: ingest_time
    type: timestamp_tz
    nullable: false
    description: 物理入库时间（审计）
    pit_role: ingest_time
  - name: provider
    type: enum
    enum: [tushare, baostock, wind, akshare, fuyao]
    nullable: false
    description: 该行来源（provider 维度，非字段品牌）
    pit_role: none
```

## 6. 校验与 CI（强制）

1. 元 schema 校验（Pydantic/JSON Schema 双向）；
2. 命名规范：字段禁 `provider` 品牌前缀/缩写（Source Independence）；
3. 类型/单位/PIT 角色合法；`pit_role` 不得缺失（`none` 显式声明）；
4. SLA 四要素完整；`coverage.universe` 明确（含退市）；`storage.read_model` 必须语义版本化；
5. 血缘无环、上游数据集存在；派生公式白名单可解析、as-of 标注完整；
6. 与实现一致性：DDL 列、v0 归一化 spec、SDK/REST 模型 ⊆ 字典（CI 比对）；
7. 语义版本规则：口径/单位变更必须升主版本，CI 检测 diff 并强制。

## 7. 生成物与消费方

| 消费方 | 生成/校验 |
|---|---|
| 存储层（TASK-3.3） | DDL / Alembic 迁移 / 分区与保留策略 |
| 归一化层（v0 spec） | `source_mappings` 与实际 adapter spec 交叉校验 |
| SDK / REST（TASK-3.7/3.11） | Pydantic 模型 + OpenAPI schema |
| WebUI（TASK-3.8） | 字典浏览页（字段/口径/血缘/覆盖率） |
| 质量平台（TASK-3.5） | `quality` 规则实例化 |
| 新鲜度面板（TASK-3.6） | `update_sla` → 告警阈值 |

## 8. 变更流程

1. 先改字典（version/deprecation 标注）→ CI 校验 → 生成/迁移 → 发布；
2. 纯增量（加字段/扩枚举）：不升版本；
3. 语义变更（口径/单位/含义）：升主版本 + Read Model `_vN` 并存过渡 + 弃用公告；
4. 删除字段：先弃用（标记 deprecated + 终止日期），过渡期后移除。

## 9. 与 v0 归一化 spec 的关系

- v0 `fin_data_hub/specs/*.toml`：**适配器级**响应字段映射（源字段 → canonical 列），随 adapter 维护；
- 平台字典：**数据集级**契约（canonical 字段的完整语义/SLA/质量/血缘/派生）；
- 二者关系：字典的 `fields[].source_mappings` 作为交叉校验来源，CI 保证"平台契约 ⊇ 适配器映射"，避免两套定义漂移。

## 10. 待评审决策

1. 格式：YAML（推荐，可注释） vs TOML（复用 v0 工具链）；
2. 文件粒度：每域一文件（推荐） vs 每数据集一文件；
3. 公式 DSL 边界：是否允许聚合窗口函数首期实现（建议首期仅行级表达式 + `last/diff/pct_change`，聚合后置）；
4. 派生数据是否逐条登记公式（建议是）与重算触发（TASK-3.12 落地）。
