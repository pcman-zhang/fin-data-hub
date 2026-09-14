# 配置手册

> 本文说明各组件的配置方式与全部配置项。
> 组件职责见 [核心组件](components.md)；故障处理见 [排障指南](troubleshooting.md)。

## 0. 总原则

- **凭证一律显式注入**：通过配置对象参数或环境变量，由调用方提供；
  库不会隐式读取用户目录、全局配置文件或任何外部状态；
- **凭证不落仓库、不进日志**：配置对象的 `repr` 已脱敏；
- **配置错误快速失败**：Runtime 配置非法时以非零码退出并给出明确原因。

## 1. 交付形态与安装

平台以**容器方式交付**：单镜像多入口（控制面 / 调度 / 执行与消费服务）与数据库
由 Docker Compose 编排，凭证与配置经环境变量注入（编排建设中，见
[系统架构](architecture.md) §8）。

开发环境（源码方式，用于贡献代码与运行测试）：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev,platform,tushare,akshare,ifind,wind,fuyao,baostock]"
```

## 2. 接入层（FinDataHub）

### 2.1 凭证

```python
from fin_data_hub import FinDataHub, HubConfig
from fin_data_hub.config import TushareConfig, WindConfig, IfindConfig, FuyaoConfig

config = HubConfig(
    tushare=TushareConfig(token="..."),
    wind=WindConfig(api_key="..."),
    ifind=IfindConfig(authorization="..."),
    fuyao=FuyaoConfig(api_key="..."),
    # AkShare 与 BaoStock 无需凭证
)
hub = FinDataHub.from_config(config)   # 缺凭证 / 缺依赖的源自动跳过
```

| 配置对象 | 参数 | 说明 |
|---|---|---|
| `TushareConfig` | `token` | Tushare 接口凭证 |
| `WindConfig` | `api_key` | Wind MCP 凭证 |
| `IfindConfig` | `authorization` | iFinD MCP 凭证 |
| `FuyaoConfig` | `api_key` / `base_url` / `max_attempts` | 可覆盖服务地址与重试次数 |
| `BaostockConfig` | `max_attempts` | 会话自动重连 |
| `AkShareConfig` | — | 本地库，无需凭证 |

### 2.2 缓存（`CacheConfig`）

| 参数 | 默认 | 说明 |
|---|---|---|
| `max_bytes` | 512 MiB | 字节预算（主约束） |
| `max_entries` | 4096 | 条数兜底 |
| `max_entry_bytes` | 64 MiB | 单条过大跳过缓存 |
| `ttl` | 6 小时 | 付费源默认缓存时长 |
| `copy_on_return` | `False` | 返回副本以隔离调用方修改 |

调用级覆盖：`hub.get_bars(..., force=True)` 跳过缓存并刷新。

### 2.3 限流（`rate_limits`）

每源独立令牌桶，在真实调用前获取令牌，等待超时抛 `RateLimitTimeout`。

| 源 | 默认 QPS |
|---|---|
| Tushare | 2 |
| AkShare | 1 |
| Wind | 1 |
| iFinD | 2 |

```python
from fin_data_hub.ratelimit import RateLimitConfig

config = HubConfig(rate_limits={"ifind": RateLimitConfig(rate=2.0, burst=2.0, timeout=30.0)})
```

注意：限流与预算是**进程内**的；多进程部署会叠加实际请求量。

### 2.4 预算与计量（`BudgetConfig`）

| 参数 | 说明 |
|---|---|
| `calls_per_day` | 按源的日调用次数上限 |
| `cost_per_day` | 按源的日成本上限 |
| `cost_table` | `"source.endpoint"` → 单次成本；支持按源兜底 |
| `warn_ratio` | 达到预算比例时告警（默认 0.8） |
| `on_alert` | 告警回调 |
| `on_record` | 每条记录回调（跨进程汇总的集成点） |

`hub.stats()` 查看当前进程的调用、成本与告警统计。

### 2.5 跨源路由（`RoutingConfig`）

| 参数 | 默认 | 说明 |
|---|---|---|
| `factor_source` | `tushare` | 复权合成使用的因子源 |
| `trusted_native_adjust` | `{tushare, akshare}` | 允许使用原生复权的源 |
| `fallbacks` | 空 | 主源失败时的回退顺序 |
| `field_fill` | `True` | 允许从补充源补全缺失字段 |

`source` 始终是主源；补全、合成与回退不改变主源语义，并在结果中标注实际执行源。
各源复权可信度与已知问题见 [数据源](data-sources.md)。

## 3. 平台存储与数据库

### 3.1 连接配置

平台由环境变量构建连接（`StorageConfig.from_env`）：

| 变量 | 必填 | 说明 |
|---|---|---|
| `DATABASE_HOST` | ✅ | 数据库主机 |
| `DATABASE_PORT` | | 默认 5432 |
| `DATABASE_USER` | ✅ | 用户名 |
| `DATABASE_PASSWORD` | ✅ | 密码 |
| `DATABASE_NAME` | | 默认 `fin_data_platform` |
| `FDP_DATABASE_HOST` | | 覆盖主机（地址变动的场景） |

`StorageConfig` 同时支持读写 DSN 分离（`write_dsn` / `read_dsn`）与
`timescale` 开关（是否启用分区 / 压缩语句）。

### 3.2 本地开发数据库

```bash
cp .env.example .env                            # 填写密码（.env 不入库）
docker compose -f docker-compose.dev.yml up -d  # 开发用 PostgreSQL + TimescaleDB
export $(grep -v '^#' .env | xargs)
```

### 3.3 版本化迁移

```bash
.venv/bin/python -c "from fin_data_platform.storage.migrations import upgrade; upgrade()"
.venv/bin/python -c "from fin_data_platform.storage.migrations import downgrade; downgrade()"
```

| 变量 | 说明 |
|---|---|
| `FDP_ALEMBIC_INI` | 指定 `alembic.ini`（部署容器内打包路径不同时使用） |
| `FDP_ALEMBIC_SCRIPT_LOCATION` | 指定迁移脚本目录 |
| `FDP_TEST_DATABASE=1` | **仅测试**：允许破坏性迁移集成测试（会清空项目表） |

基线由数据字典生成；字典变更必须新增迁移修订。

## 4. Runtime（控制面）

### 4.1 启动

```bash
.venv/bin/python -m fin_data_platform.runtime --role all
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `--role` | `all` | `all`（单机）/ `scheduler`（仅调度分发）/ `worker`（仅执行） |
| `--workers` | 2 | 工作线程数 |
| `--log-level` | `INFO` | 日志级别 |

退出码：`0` 正常停止；`1` 启动健康检查未通过；`2` 配置非法。

### 4.2 同步任务（环境变量）

| 变量 | 必填 | 说明 |
|---|---|---|
| `FDP_SYNC_CODES` | ✅ | canonical 代码清单，逗号分隔（如 `600519.SH,000001.SZ`）；未设置时不装配同步任务 |
| `FDP_SYNC_START` | ✅ | 首次窗口起点（ISO 日期 `YYYY-MM-DD`），用于水位缺失时的补数 |
| `FDP_SYNC_SOURCE` | ✅ | 数据源（`tushare` / `akshare` / `ifind` / `wind` / `fuyao` / `baostock`），必须显式指定 |
| `FDP_SYNC_SCHEDULE` | | 5 段 cron（UTC）或 `interval:<秒>`；缺省为轮询追平（启动即补，不设定时） |
| `TUSHARE_TOKEN` | 按需 | 数据源凭证（亦可 `FIN_DATA_HUB_TUSHARE_TOKEN`） |

```bash
export TUSHARE_TOKEN=...
export FDP_SYNC_CODES=600519.SH
export FDP_SYNC_START=2026-09-01
export FDP_SYNC_SOURCE=tushare
export FDP_SYNC_SCHEDULE='0 9 * * 1-5'
.venv/bin/python -m fin_data_platform.runtime --role all
```

行为：启动即从水位追平到最近已收盘交易日，成功后推进水位；失败按运行记录
重试；调度注册持久化，进程重启不丢。

### 4.3 运行时参数（`RuntimeConfig`）

| 参数 | 默认 | 说明 |
|---|---|---|
| `role` | `all` | 进程角色 |
| `worker_count` | 2 | 工作线程数 |
| `tick_interval` | 1.0 s | 调度到期计算间隔 |
| `worker_interval` | 0.2 s | 工作池轮询间隔 |
| `max_queued` | 100 | 背压上限（排队 + 重试中） |
| `check_dictionary` | `True` | 启动校验字典 |
| `check_schema` | `True` | 启动校验数据库 schema |

## 5. 测试用环境变量

集成测试读取（库本身不读取这些变量，仅测试使用）：

| 变量 | 用途 |
|---|---|
| `FIN_DATA_HUB_TUSHARE_TOKEN` | Tushare 集成测试 |
| `FIN_DATA_HUB_WIND_API_KEY` | Wind 集成测试 |
| `FIN_DATA_HUB_IFIND_TOKEN` | iFinD 集成测试 |
| `FIN_DATA_HUB_FUYAO_API_KEY` | Fuyao 集成测试 |
| `DATABASE_*` / `FDP_DATABASE_HOST` | 存储集成测试 |
| `FDP_TEST_DATABASE=1` | 允许破坏性迁移测试 |

```bash
.venv/bin/python -m pytest                    # 离线单测（默认跳过集成）
.venv/bin/python -m pytest -m integration     # 端到端（需凭证 / 数据库）
```
