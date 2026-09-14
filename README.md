# FinDataPlatform（金融数据基础设施）

FinDataPlatform 是一个具备 **Point-In-Time（PIT）语义**的金融数据底座，解决：

- **多源数据统一**：canonical 代码、字段与口径统一，源差异在接入层收敛；
- **历史可回溯（As-Of）**：事件时间与知识时间双轴，任意时点可复现当时可见的数据；
- **数据重述（Restatement）**：公告修正 / 财务重述以新版本追加，不改写历史；
- **实体身份管理**：Entity Graph（issuer / listing / 关系 / 外部标识）与 PIT Universe；
- **派生指标治理**：算法登记与派生口径可追溯（Derived Engine）；
- **统一数据出口**：语义版本化的 Read Model，供研究、回测与下游系统消费。

```
多源金融数据 → Canonical Schema → PIT Storage → Derived Data → Read Model → 消费层（SDK / REST / Export / …）
```

> 项目处于开发阶段，暂无外部使用者。

## 系统架构

平台不是应用后端，而是数据基础设施（与 Iceberg / Delta Lake 类似：元数据、存储与快照语义才是主体，API 只是入口）。

```
                 ┌──────────────┐
                 │ Data Sources │   Tushare / Wind / iFinD / AkShare / Fuyao / BaoStock
                 └──────┬───────┘
                        │
                  FinDataHub            接入层：唯一数据源访问面（适配 / 归一 / 限流 / 缓存；不落数据）
                        │
        ┌───────────────┼───────────────┐
        │               │               │
   Dictionary      Entity Registry    Storage
   契约 / 血缘      身份 / 关系 / PIT   Raw → Canonical → Mart
        │               │               │
        └───────────────┼───────────────┘
                        │
                  Derived Engine        派生引擎：算法登记 / as-of 输入 / 重述
                        │
                    Read Models         语义版本化的只读出口（mart.*_v）
                        │
        ┌───────────────┼───────────────┬───────────┐
        │               │               │           │
      SDK            REST           Export      (MCP…)
```

分层职责：

- **Platform Core（平台主体）**：Dictionary（数据契约）· Entity Registry（实体身份）· Storage（PIT 存储）· Derived Engine（派生治理）——平台语义与壁垒都在这一层；
- **Consumption Adapter（消费适配器）**：SDK · REST · Export · MCP——可选入口，不承载平台语义，也不是平台主体。

按现代数据平台的三平面理解：

- **Control Plane（`meta`）**：数据集注册、任务运行、watermark、质量结果、数据代次、算法注册与重述台账（`doc-13` §1）；
- **Data Plane**：`raw`（源端原始）→ Canonical（按域的标准化表 + PIT 字段）→ `mart`（Read Model）；
- **Consumption Plane**：SDK / REST / 批量导出 / 未来 MCP——只读适配器，不改变数据语义。

### Platform Core（平台四大件）

- **数据字典（Dictionary）**：机读契约（字段 / 类型 / 单位 / PIT 角色 / 质量规则 / 血缘 / 映射）；schema、迁移与文档由字典生成或强校验（Schema First，`doc-11`）。
- **实体注册表（Entity Registry）**：Entity Graph——实体身份与分类面、代码履历、关系（词表驱动双向查询）、外部标识；交易状态归数据集，PIT Universe 由数据集推导（`doc-10` §3.3）。
- **PIT 存储（Storage）**：Raw → Canonical → Read Model 分层；事件时间与知识时间双轴；append-only 幂等写入；hypertable 分区与压缩；Alembic 版本化迁移（`doc-13`）。
- **派生引擎（Derived Engine）**：存输入与算法，不存派生结果的多版本；算法登记（`algorithm_id`）与重述台账；as-of 输入防前视（`doc-10` §3.5）——**建设中**（TASK-3.12）。

### FinDataHub → 数据库（数据流）

1. **采集**：FinDataHub 按显式 `source` 调用数据源（Tushare / Wind / iFinD / AkShare / Fuyao / BaoStock），输出 canonical 代码与标准字段；每源限流与 TTL 缓存约束调用量与成本。
2. **归一化**：平台写入端以**数据字典**为唯一契约（Schema First）——字段名/类型/单位/PIT 角色由字典定义，源字段映射登记在 `mappings`，供应商特有字段不进入公共 schema。
3. **PIT 落地**：写入携带事件时间与知识时间（如公告日 → `knowledge_time`）、`ingest_time`、`version`；append-only，物理键幂等（`ON CONFLICT DO NOTHING`）。
4. **时序化**：按字典声明的分区策略建立 hypertable 与压缩策略（行情按事件时间、版本化数据按知识时间）。

现状：数据源适配、数据字典、幂等写入、schema 与迁移已落地；**采集调度与增量同步（TASK-3.6）尚在建设**，当前落库经由迁移工具与导入通道（TASK-3.3.2 建设中）执行。

### 数据库如何存储与组织

- **Schema 分层**（`doc-13`）：
  - `raw`：源端原始响应，审计/重放（规划）；
  - `<domain>`：Canonical 标准表，与数据域同名（`cn_equity` / `cn_fund` / …）；
  - `mart`：Read Model（语义版本视图，`_v<semantic_version>`）；
  - `ref`：参照数据（实体注册表、关系、外部标识、代码履历）；
  - `meta`：控制面元数据（调度 / 质量 / 派生登记，规划）。
- **表形态**：时序事实 → hypertable（`daily_bar` / `adj_factor` / `cn_fund.nav`，分区 + 压缩）；版本化时序 → 按 `knowledge_time` 分区（`financials_balance_sheet`）；SCD2 属性区间（`ref.entity` / `index_member` / `listing_lifecycle`）；快照（`index_weight`）。
- **PIT 双轴**：事件时间（`trade_date` / `end_date`）与知识时间（发布 / 入库）分离；as-of 查询 = 「知识时间 ≤ as_of 且按业务键取最新版本」，Canonical 不落 `is_latest` 列。
- **Entity Graph（`ref`）**：实体身份与分类面（`entity`）、代码履历（`entity_code_history`）、关系（`entity_relation` + 词表 `relation_type_dict`，单向存储、词表驱动双向查询）、外部标识（`entity_external_id`：ISIN/LEI/USCC 等）；交易状态归数据集（`cn_equity.listing_lifecycle`），PIT Universe 由数据集推导。
- **读模型**：`mart.entity_latest_v1`（当前态视图）与 `mart.entity_asof(ts)`（属性 as-of 表函数）已落地；其余数据集读模型已在字典声明，随消费层建设生成。
- **迁移**：Alembic 版本化；基线由数据字典生成（含 hypertable / 压缩 / 读模型），`upgrade()` / `downgrade()` 幂等可重复。
- 自动生成文档：表 / 字段 / 依赖（`doc-17`）、数据目录（`doc-19`）。

### Consumption Adapter（消费适配器）

平台提供多种只读出口（建设中），SDK/REST 只是其中两种适配器：

- **SDK 直连 Read Model**（SDK direct mode，`doc-12`）：不必经过 API Server；
- **REST**：薄封装（`doc-12`；TASK-3.7）；
- **批量导出 / DuckDB**：研究通道（TASK-3.10）；
- 未来 MCP 等。

消费层只读 `mart`，不直读 Raw / Canonical 物理表。

当前仓库内已可用的能力（开发/运维用法）：

- `fin_data_platform.dictionary`：字典加载 / CI 校验 / 数据目录；
- `fin_data_platform.registry`：实体注册、代码解析、关系与外部标识、PIT Universe；
- `fin_data_platform.storage`：按字典生成 schema、幂等写入、as-of / latest 读取、实体读模型；
- `fin_data_platform.storage.migrations`：Alembic 升级 / 回滚。

当前平台核心能力（Dictionary / Registry / Storage / Migration）可作为**纯库**运行，不依赖常驻服务进程；REST / MCP / 调度器属于**可选**的消费或运维组件。目前 `docker-compose.dev.yml` 只运行开发用 TimescaleDB（PostgreSQL 17）数据库。

## 当前状态

| 平台能力 | 状态 |
|---|---|
| 数据字典（契约 / CI 校验 / 数据目录 / 血缘） | ✅ 已落地（`doc-11` / `doc-17` / `doc-19`） |
| 实体注册表 Entity Graph（身份 / 关系 / 外部标识 / PIT Universe） | ✅ 已落地（`doc-10` §3.3） |
| PIT 存储（schema 生成 / 幂等写入 / as-of 读取 / 实体读模型） | ✅ 已落地（`doc-13`） |
| 版本化迁移（Alembic，字典生成基线） | ✅ 已落地 |
| 数据源接入 FinDataHub（多源适配 / Router / 限流 / 缓存 / 计量） | ✅ 可用 |
| 派生引擎 / 时序查询能力 | 🚧 建设中（TASK-3.12 / 3.13） |
| Control Plane（`meta`：质量 / 调度 / 代次 / 算法台账） | 🚧 建设中（TASK-3.5 / 3.6 / 3.12） |
| 采集调度与增量同步 / Parquet-CSV 导入通道 | 🚧 建设中（TASK-3.3.2 / 3.6） |
| 消费层（SDK / REST / 管理台 / 批量导出 / MCP） | 🚧 建设中（TASK-3.7 / 3.8 / 3.10 / 3.11） |
| 部署（Docker Compose 编排：数据库 / 服务） | 🚧 仅 dev 数据库；应用编排 TASK-3.4 |

设计文档（Backlog）：`doc-10` 架构总纲、`doc-11` 数据字典规范、`doc-12` REST 契约、`doc-13` 存储策略、`doc-17` 数据库设计、`doc-18` 代码与标识标准、`doc-19` 数据目录。

## 安装

平台使用者通过**只读客户端**消费 Read Model（SDK direct mode 或经服务；建设中，见 `doc-12` / TASK-3.7 / 3.11）：

```bash
pip install fin-data-platform
```

接入层（数据源采集/回填）由独立包 `fin-data-hub` 提供（**预留包名，当前未单独发布**）：源码位于本仓库 `src/fin_data_hub`，仅供采集侧与开发使用，平台客户端使用者无需安装数据源依赖。

核心依赖仅 `pandas`。iFinD / Wind 通过厂商远端 MCP（HTTP JSON-RPC）接入，**不需要安装 WindPy / iFinDPy**。

版本：单一来源 `src/fin_data_hub/_version.py`（`pyproject.toml` 动态读取）。

## 当前用法（Python 库，开发/运维）

以下为仓库内已可用的平台能力（面向开发与运维）；面向使用者的只读客户端（SDK/REST）在建设中，交付形态见「FinDataPlatform 如何使用」。

```python
from fin_data_platform.dictionary import catalog_markdown, load_all, validate_directory
from fin_data_platform.registry import EntityRegistry
from fin_data_platform.storage import build_metadata, ensure_schema

# 1) 数据字典：CI 校验 / 数据目录（我们有哪些数据、怎么获取）
assert validate_directory() == []
specs = load_all()

# 2) 实体注册表：注册 / 解析 / 关系 / 外部标识
registry = EntityRegistry()
listing = registry.register(
    code="600519.SH", entity_type="equity", name="贵州茅台", market="cn"
)
issuer = registry.register_issuer(code="91520000714308124W", name="贵州茅台酒股份有限公司")
registry.link_issuer(listing.entity_id, issuer.entity_id)
registry.add_external_id(listing.entity_id, "isin", "CNE0000018R8")

# 3) 存储：按字典生成 schema（幂等；需要数据库连接）
metadata, specs = build_metadata()
# ensure_schema(engine, metadata=metadata, specs=specs)
```

## 本地数据库与迁移

```bash
cp .env.example .env          # 填写密码（.env 不入库）
docker compose -f docker-compose.dev.yml up -d   # 开发用 PostgreSQL 17 + TimescaleDB（仅数据库）
export $(grep -v '^#' .env | xargs)

# 版本化迁移（Alembic；基线由数据字典生成）
.venv/bin/python -c "from fin_data_platform.storage.migrations import upgrade; upgrade()"
# 回滚：downgrade()（等价 alembic downgrade base）
```

- 基线文件：`migrations/versions/0001_baseline.py`（`write_baseline()` 由字典生成；漂移校验见 `tests/test_platform_migrations.py`）。
- 数据库设计（表 / 字段 / 依赖）见 `doc-17`；存储 schema 策略见 `doc-13`。

## 接入层（fin_data_hub）

> 独立包 `fin-data-hub`（**预留包名，当前未单独发布**，随本仓库 `src/fin_data_hub` 提供）；数据源适配、限流与内存缓存；仅在采集 / 回填场景直接使用。

### 特性

- **统一代码模型**：以 WindCode 风格 `symbol.VENUE` 作为标的主键（如 `600000.SH`、`000001.SZ`、`510300.SH`、`000001.OF`），各源代码差异由映射层收敛。
- **统一接口 + 显式来源**：取数接口通过 `source` 参数明确数据来源，内部按 source 调度到对应适配器。
- **配置注入**：Tushare token、Wind / iFinD 凭证由调用方通过配置对象传入；库不读取环境变量、全局配置或用户目录。
- **能力驱动的请求合并**：按各源/端点上限自动分块（如单标的源逐代码、Wind 快照 ≤50、iFinD EDB 多指标聚合）并合并去重。
- **每源限流**：令牌桶（QPS）在适配器调用边界生效，可按源覆盖；等待超时抛出 `RateLimitTimeout`。
- **Router 跨源路由**：统一输出；缺字段 / 缺复权 / 主源失败时按策略补充（字段补全、raw + factor 复权合成、失败回退），结果带溯源（`doc-5`）。
- **线程安全**：共享状态加锁、缓存 single-flight，避免并发重复请求消耗配额。
- **内存缓存**：TTL + LRU + 字节预算，`force=True` 跳过缓存强制刷新。
- **调用计量**：按源统计调用次数与估算成本、预算告警，`hub.stats()` 查看；跨进程汇总通过 `on_record` 回调。

### 快速开始

```python
from fin_data_hub import FinDataHub, HubConfig, Source
from fin_data_hub.config import TushareConfig, WindConfig, IfindConfig

config = HubConfig(
    tushare=TushareConfig(token="..."),
    wind=WindConfig(api_key="..."),
    ifind=IfindConfig(authorization="..."),
    # akshare 无需凭证
)

# 按配置自动装配可用数据源（缺凭证/依赖的源会被跳过）
hub = FinDataHub.from_config(config)

# 日线行情：显式指定数据源
bars = hub.get_bars(
    ["600000.SH", "510300.SH"],
    start="2026-09-01",
    end="2026-09-11",
    source=Source.TUSHARE,
)

# 强制刷新（跳过缓存）
bars = hub.get_bars(
    ["600519.SH"], "2026-09-09", "2026-09-11",
    source=Source.WIND, force=True,
)

# 场外基金净值（iFinD 支持多基金合并为一次调用）
nav = hub.get_fund_nav(["000001.OF"], source=Source.IFIND)

# 交易日历与参考数据
calendar = hub.get_trade_calendar(start="2026-09-01", end="2026-09-11", source=Source.AKSHARE)
stocks = hub.get_reference("stock_list", source=Source.TUSHARE)

# 缓存与调用统计（内存）
stats = hub.stats()
```

也可以手动装配：

```python
from fin_data_hub.sources import SourceRegistry
from fin_data_hub.sources.tushare import TushareAdapter

registry = SourceRegistry([TushareAdapter(config.tushare)])
hub = FinDataHub(config, registry=registry)
```

### 统一代码模型

格式为 `symbol.VENUE`：

| 示例 | 含义 |
|---|---|
| `600000.SH` / `000001.SZ` / `920002.BJ` | A 股（沪 / 深 / 北） |
| `510300.SH` / `159915.SZ` | 场内 ETF / LOF |
| `000001.OF` | 场外基金 |
| `000300.SH` / `399006.SZ` | 指数 |

- 代码统一 6 位补零、VENUE 大写；`000001.SZ`（平安银行）与 `000001.OF`（华夏成长）必须靠后缀区分，不接受裸代码。
- Tushare、Wind、iFinD 直接接受该格式；AkShare 由映射层转换为 6 位或接口专有格式。

### 各源支持范围

| 能力 | Tushare | AkShare | Wind | iFinD |
|---|---|---|---|---|
| `get_bars` | ✅ 日线，支持 qfq/hfq | ✅ 股票 / ETF / LOF / 指数 | ⚠️ 仅日线、单代码逐次调用 | ⚠️ 仅指数 |
| `get_snapshot` | — | — | ✅ 单次 ≤50 代码 | — |
| `get_fund_nav` | ✅ | ✅ 场外基金 | — | ✅ 多基金合并 |
| `get_reference` | ✅ 股票 / 基金 / ETF / 退市 / 申万分类 / 指数列表 | — | — | — |
| `get_security_info` | ✅ 标的/ETF/基金/指数基础信息（按代码） | — | — | — |
| `get_index_weights` | ✅ 指数成分与权重（月度快照） | — | — | — |
| `get_financials` | ✅ 资产负债表 / 财务指标（核心列） | — | — | — |
| `get_market_events` | ✅ 新股 / 停复牌 / ST 名单 / 名称变更 | — | — | — |
| `get_trade_calendar` | ✅ | ✅ | — | — |
| EDB 宏观指标 | — | — | ✅ 精确代码批量 | ✅ 多指标聚合 |
| 债券行情 | — | — | ✅ 长区间 ≤90 天分块 | — |

限制说明：

- Wind 日线不传 `period`（后端不接受 `period=1d`）；K 线为单代码接口，多代码由库逐次调用。
- iFinD 的 K 线目前仅支持指数（`index_data`）；场外基金净值走 `get_fund_market_performance`（NL 聚合）。
- iFinD 的 NL 工具普遍支持多标的/多指标聚合（已抽验 stock/fund/edb），库内合并为一次调用，不做逐标的拆分；单次 50 代码为请求体积的安全上限。
- AkShare 无参考数据接口；各接口为单标的形式，批量请求由库自动拆分。
- BaoStock：仅支持 SH/SZ（`sh.600000`/`sz.399006`，含指数）；原生复权不列入 Router 可信源；连接断开会自动重新 login（会话按代际 + 引用计数管理）。
- Tushare 行情按资产类型路由：股票 `daily`、ETF/LOF `fund_daily`、指数 `index_daily`；复权因子股票走 `adj_factor`、ETF/LOF 走 `fund_adj`（指数无因子，请求复权会明确报错）。
- Fuyao：`get_snapshot`（批量）、`get_bars`（单标的，窗口 ≤10 年自动分块）、`get_reference`（stock/fund/index 列表）、`get_trade_calendar`（近一年窗口）；当前免费、动态限流（HTTP 429 / code=4001 退避重试）。
- **Fuyao 原生复权不可用**：其预计算复权序列经对账异常（`doc-4`）。请求复权时 Router 自动组合「Fuyao 原始价 + Tushare 因子」合成（需配置 Tushare；见 `doc-5`）；直接调用适配器时仅支持 `adjust=None`。

### 配置与凭证

- 凭证一律显式注入：`HubConfig(tushare=..., wind=..., ifind=...)`；缺失凭证且调用该源时抛出 `MissingCredentialError`。
- 凭证不写入日志，配置对象的 `repr` 已脱敏。
- 如需自定义各源限制与预算，通过 `HubConfig` 的 `cache` / `budget` 子配置：

```python
from fin_data_hub import BudgetConfig, CacheConfig, HubConfig

config = HubConfig(
    cache=CacheConfig(max_bytes=256 * 1024 * 1024, ttl=6 * 3600),
    budget=BudgetConfig(
        calls_per_day={"wind": 50},
        cost_table={"wind.get_economic_data": 10.0},
        on_record=lambda record: my_sink(record),  # 跨进程汇总入口
    ),
)
```

### 限流

- 每源独立令牌桶（QPS），在适配器真实调用前获取令牌；等待超时抛出 `RateLimitTimeout`。
- 默认值（保守起步）：Tushare 2 QPS、AkShare 1 QPS、Wind 1 QPS、**iFinD 2 QPS**。
- 按源覆盖：

```python
from fin_data_hub import HubConfig
from fin_data_hub.ratelimit import RateLimitConfig

config = HubConfig(
    rate_limits={"ifind": RateLimitConfig(rate=2.0, burst=2.0, timeout=30.0)}
)
```

- 限流为进程内限制；多进程部署会叠加实际请求量。

### 缓存与刷新

- 进程内 TTL + LRU 缓存，付费源默认 6h；`force=True` 跳过缓存并覆盖写入。
- 内存约束：`max_bytes`（字节预算，主约束）+ `max_entries`（条数兜底）+ `max_entry_bytes`（单条过大跳过缓存）。
- 结果 `df.attrs` 携带 `source / cached / fetched_at` 等元信息。
- 缓存仅存于内存，进程退出即失效；本库不负责任何持久化。

### 调用计量

- `hub.stats()` 返回缓存与用量统计（按日调用次数、估算成本、告警）。
- 计量仅统计当前进程；跨进程汇总由调用方在 `BudgetConfig.on_record` 中写入自有存储或指标系统。

## 开发

仓库结构：

```
src/fin_data_hub/        接入层（数据源适配、限流、缓存）
src/fin_data_platform/   平台层（dictionary / registry / storage）
migrations/              Alembic 迁移（基线由数据字典生成）
tests/                   单元测试与集成测试（-m integration）
backlog/                 任务与设计文档（Backlog.md CLI 管理）
```

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev,platform,tushare,akshare,ifind,wind,fuyao,baostock]"

.venv/bin/python -m pytest              # 离线单测（默认跳过 integration）
.venv/bin/python -m pytest -m integration   # 端到端测试（需真实凭证；存储集成另需数据库）
.venv/bin/python -m ruff check .
.venv/bin/python -m mypy
```

集成测试读取的环境变量（仅测试使用，库本身不读取环境变量）：

- `FIN_DATA_HUB_TUSHARE_TOKEN`
- `FIN_DATA_HUB_WIND_API_KEY`
- `FIN_DATA_HUB_IFIND_TOKEN`
- `FIN_DATA_HUB_FUYAO_API_KEY`

存储集成测试（`tests/test_integration_storage.py`、`tests/test_integration_migrations.py`）读取 `DATABASE_HOST / DATABASE_PORT / DATABASE_USER / DATABASE_PASSWORD`（`DATABASE_NAME` 可选，默认 `fin_data_platform`）；地址变动时可用 `FDP_DATABASE_HOST` 覆盖。

`tests/test_integration_migrations.py` 会 **DROP 目标库全部项目表**，需显式开启且指向 dev 库：

```bash
FDP_TEST_DATABASE=1 .venv/bin/python -m pytest -m integration
```

架构与设计文档见 `doc-10` ~ `doc-19`（如 `backlog doc view doc-10`）。

## 许可证

本项目采用 [MIT License](LICENSE)。

Copyright (c) 2026 Freeman Zhang
