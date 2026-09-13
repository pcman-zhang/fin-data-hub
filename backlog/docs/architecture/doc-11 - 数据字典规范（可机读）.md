---
id: doc-11
title: 数据字典规范（可机读）
type: specification
created_date: '2026-09-13 12:16'
updated_date: '2026-09-13 12:19'
---
# 数据字典规范（可机读）

> 状态：评审中（第 2 稿） | 关联：doc-10（架构总纲 §6.1 Schema First）、TASK-3.1/3.2/3.12/3.14
> 第 2 稿变更（采纳评审）：① `semantic_version` 为整数（仅主版本）；② decimal 必带 `precision/scale`；③ 拆 `business_key` / `physical_key`；④ 质量规则支持**跨字段表达式**；⑤ `source_mappings` 移出 field，改为 dataset 级 `mappings`；⑥ `coverage` 增加可计算维度；⑦ `lineage` 强制；⑧ **字典不登记公式**——派生仅登记 `inputs/output/owner`，公式归 TASK-3.12 派生引擎。

## 1. 原则

1. **Schema First**：Dictionary → Schema → SDK/API；禁止"代码先写、文档后补"；
2. **覆盖完整**：每个 DataPanel 必须登记字段/类型/单位/PIT 类别/约束/血缘/SLA/覆盖/存储/质量；
3. **Provider 无关**（doc-10 §6.2）：canonical 字段不得含供应商品牌/缩写；源差异经 `mappings` 登记，不进入公共 schema；
4. **语义版本**：`semantic_version`（整数，仅主版本）；纯增量不升，口径/单位/语义变化 +1；
5. **血缘强制**：所有 DataPanel 必须有 `lineage`（源数据用 `upstream: []` + `transform: raw` 显式声明，区分"无血缘"与"漏写"）；
6. **公式不入字典**：字典只登记派生依赖（`inputs/output/owner`）；公式文本、版本与重算策略由 TASK-3.12 派生引擎注册表管理，避免出现两套 DSL；
7. **机读优先**：可被程序解析、校验、生成；人读文档由字典渲染。

## 2. 文件形态与目录

- 格式：**YAML** + **Pydantic v2** 严格校验；元 schema 由模型导出（JSON Schema，CI 双向校验）；
- 目录：`platform/dictionary/<domain>.yaml`（每域一文件）；元 schema：`platform/dictionary/_schema/dictionary.schema.json`；
- 命名：`dataset` = `{domain}.{dataset}`（小写蛇形）；字段小写蛇形、禁止源前缀；provider 维度用 `mappings`/`provider` 字段表达。

## 3. 条目结构（meta-schema）

### 3.1 dataset 级

| 键 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `dataset` | str | ✅ | `{domain}.{dataset}`，全局唯一 |
| `semantic_version` | int | ✅ | 语义主版本（1、2…）；增量不升 |
| `domain` | enum | ✅ | doc-10 §3.1 的 DataDomain |
| `description` | str | ✅ | 口径、用途、注意事项 |
| `pit_class` | enum | ✅ | `market` / `versioned` / `scd2` / `snapshot` |
| `business_key` | [str] | ✅ | 业务主键（如 `[security_id, trade_date]`） |
| `physical_key` | [str] | ✅ | 物理唯一键（append-only：`business_key + knowledge_time + version`） |
| `grain` | str | ✅ | 粒度描述 |
| `update_sla` | obj | ✅ | `{frequency, earliest_available, latest_available, tolerance}` |
| `sources` | [obj] | ✅ | `[{provider, endpoint, note?}]`（采集入口） |
| `coverage` | obj | ✅ | `{universe, universe_source, history_start, expected_dates}`（可计算覆盖率，见 §3.3） |
| `storage` | obj | ✅ | `{canonical_table, read_model, partition_by, retention}` |
| `quality` | [obj] | ✅ | 规则列表（§3.4，含跨字段表达式） |
| `lineage` | obj | ✅ | `{upstream: [{dataset, fields?}], transform}`（源数据为 `upstream: []` + `transform: raw`） |
| `derived` | [obj] | | 派生登记：`[{output, inputs, owner}]`（**不含公式**） |
| `mappings` | [obj] | ✅ | 源映射：`[{provider, endpoint, fields: {canonical: source}}]`（§3.5） |
| `fields` | [obj] | ✅ | 字段列表（§3.2） |

### 3.2 field 级

| 键 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | str | ✅ | canonical 字段名（provider 无关） |
| `type` | enum | ✅ | `int64 / float64 / decimal / string / bool / date / timestamp / timestamp_tz / enum` |
| `precision` / `scale` | int | decimal 必填 | 如 `precision: 20, scale: 6` → DDL `NUMERIC(20,6)`（price/nav/market_value 等必须精确） |
| `unit` | str? | | 元/股/%/点…；百分数需注明 |
| `nullable` | bool | ✅ | 是否可空 |
| `enum` | [str] | | type=enum 时必填 |
| `range` | obj | | `{min, max}` |
| `description` | str | ✅ | 含义与口径 |
| `pit_role` | enum | ✅ | `event_time / publish_time / knowledge_time / ingest_time / none` |

### 3.3 coverage（可计算）

```yaml
coverage:
  universe: A 股（含退市）
  universe_source: cn_equity.security_master      # 期望实体集合来源
  history_start: 1990-12-19
  expected_dates:
    calendar: cn_equity.trade_calendar            # 期望日期集合来源
    frequency: daily
```

覆盖率（CI/质量平台自动计算）：`实际行数 / (期望实体数(as-of) × 期望日期数)`；避免覆盖率停留在描述文字。

### 3.4 quality 规则（含跨字段表达式）

| rule | 参数 | 示例 |
|---|---|---|
| `unique` | `keys` | `keys: [security_id, trade_date]` |
| `not_null` | `fields` | |
| `range` | `field, min, max` | `volume >= 0` |
| `enum` | `field, values` | |
| `expression` | `expr, severity` | `expr: "high >= low and low <= close <= high"`；`expr: "amount >= 0"` |
| `reconcile` | `against` | 与 Raw/外部源对账（TASK-4.1） |
| `freshness` | `sla, tolerance` | |

`expression` 支持跨字段/跨列约束，字段必须存在于本数据集；表达式语言与派生引擎共用（TASK-3.12），字典只登记文本与严重级别。

### 3.5 mappings（dataset 级，Schema 与 Adapter 分离）

```yaml
mappings:
  - provider: tushare
    endpoint: daily
    fields:
      close: close
      volume: vol
      amount: amount
  - provider: baostock
    endpoint: query_history_k_data_plus
    fields:
      close: close
      volume: volume
```

- 每个 provider 一段映射；canonical 字段 → 源字段（含单位换算标注可后续扩展）；
- field 级不再出现 `source_mappings`，避免单字段挂 100+ 源映射导致的膨胀；
- 与 v0 `fin_data_hub/specs/*.toml` 交叉校验：平台 `mappings` ⊇ 适配器映射。

## 4. 派生数据：只登记依赖，不登记公式

```yaml
derived:
  - output: qfq_close
    inputs: [cn_equity.daily_bar.close, cn_equity.adj_factor.adj_factor]
    owner: derived-engine
```

- 公式文本、版本、重算与 as-of 策略：由 **TASK-3.12 派生引擎**的注册表管理（单一语言，DuckDB SQL/引擎函数）；
- 字典职责：血缘 + 依赖关系 + 输出字段 + 责任方；CI 校验 inputs 存在、血缘无环；
- 理由：窗口/跨表/横截面/中性化等需求会让"字典公式"演变成半个 SQL，形成两套语言（DSL vs SQL）的维护灾难。

## 5. 完整示例：`cn_equity.daily_bar`

```yaml
dataset: cn_equity.daily_bar
semantic_version: 1
domain: cn_equity
description: A 股日线行情（不复权原始价；复权价按 raw + factor、as-of 计算）
pit_class: market
business_key: [security_id, trade_date]
physical_key: [security_id, trade_date, knowledge_time, version]
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
  universe: A 股（含退市）
  universe_source: cn_equity.security_master
  history_start: 1990-12-19
  expected_dates:
    calendar: cn_equity.trade_calendar
    frequency: daily
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
  - rule: expression
    expr: "high >= low and low <= close <= high"
    severity: error
  - rule: reconcile
    against: raw_stock_daily
lineage:
  upstream: []
  transform: raw
derived:
  - output: qfq_close
    inputs: [cn_equity.daily_bar.close, cn_equity.adj_factor.adj_factor]
    owner: derived-engine
mappings:
  - provider: tushare
    endpoint: daily
    fields:
      close: close
      volume: vol
      amount: amount
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
    type: decimal
    precision: 24
    scale: 4
    unit: 元
    nullable: true
    description: 成交额（精确金额）
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
  - name: version
    type: int64
    nullable: false
    description: 同业务键的版本号（append-only）
    pit_role: none
  - name: provider
    type: enum
    enum: [tushare, baostock, wind, akshare, fuyao]
    nullable: false
    description: 该行来源（provider 维度）
    pit_role: none
```

## 6. 校验与 CI（强制）

1. 元 schema 校验（Pydantic/JSON Schema 双向）；
2. `semantic_version` 为整数；口径/单位/语义 diff 必须 +1（CI 检测强制）；
3. 命名规范：字段禁源品牌前缀/缩写（Source Independence）；
4. decimal 必须带 `precision/scale`；类型/PIT 角色合法且 `pit_role` 显式（含 `none`）；
5. `business_key` 与 `physical_key` 齐备，`physical_key ⊇ business_key + knowledge_time + version`；
6. `lineage` 必填（源数据显式 `raw`）；血缘无环、上游存在；`derived.inputs` 存在；
7. `quality.expression` 可解析且字段存在；`coverage` 四要素完整可计算；
8. `mappings` 与 v0 归一化 spec 交叉校验（平台 ⊇ 适配器）；`storage.read_model` 语义版本化。

## 7. 生成物与消费方

| 消费方 | 生成/校验 |
|---|---|
| 存储层（TASK-3.3） | DDL / Alembic 迁移 / 分区与保留（decimal 精度直出） |
| 派生引擎（TASK-3.12） | 读取 `derived.inputs/output` 注册公式与重算 |
| 归一化层（v0 spec） | `mappings` 交叉校验 |
| SDK / REST（TASK-3.7/3.11） | Pydantic 模型 + OpenAPI |
| WebUI（TASK-3.8） | 字典浏览（字段/口径/血缘/覆盖率） |
| 质量/新鲜度（TASK-3.5/3.6） | quality 规则实例化；SLA → 告警阈值 |

## 8. 变更流程

1. 字典先行 → CI 校验 → 生成/迁移 → 发布；
2. 纯增量（加字段/扩枚举）：不升 `semantic_version`；
3. 语义变更（口径/单位/含义）：`semantic_version + 1` + Read Model `_vN` 并存 + 弃用公告；
4. 删除字段：先弃用（deprecated + 终止日期），过渡后移除。

## 9. 与 v0 归一化 spec 的关系

- v0 `fin_data_hub/specs/*.toml`：**适配器级**响应映射（源字段 → canonical），随 adapter 维护；
- 平台 `mappings`（dataset 级）：平台契约侧的源映射登记；
- 关系：CI 保证"平台 mappings ⊇ 适配器 spec"，两处映射漂移即失败。

## 10. 待评审决策

1. 格式：YAML（推荐）vs TOML；
2. 文件粒度：每域一文件（推荐）vs 每数据集一文件；
3. `quality.expression` 与派生引擎共用表达式语言的首期范围（建议：比较/逻辑/算术 + 显式字段引用；聚合/窗口后置）；
4. `mappings.fields` 是否需要记录单位换算与枚举映射（建议首期只记字段名，换算在适配器 spec）。
