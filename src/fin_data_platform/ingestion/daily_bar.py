"""最小 Sync Engine：FinDataHub → Canonical（doc-10 §3.2 写入端，单数据集起步）。

本切片只做日线行情（``cn_equity.daily_bar``）：单标的一段窗口，取数 → canonical
行映射 → 幂等追加（``append_rows``）。

PIT 语义：

- ``knowledge_time``：首版取交易日收盘时刻（15:00 CST = 07:00 UTC，稳定值，保证
  重跑幂等）；检测到源值修订时取修订入库时刻（当日可见）；
- ``publish_time``：源未提供，置空（可得时间以 ``knowledge_time`` 表达）；
- ``version``：同一业务键的 append-only 版本号；值未变化不写新版本，变化则追加
  新版本（重述，不改写历史）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, time
from functools import lru_cache
from typing import Any

import pandas as pd
from sqlalchemy import Engine, select

from fin_data_platform.registry._util import to_date
from fin_data_platform.registry.store import EntityStore
from fin_data_platform.runtime._util import utcnow
from fin_data_platform.storage.schema import build_metadata
from fin_data_platform.storage.writers import append_rows

#: 目标数据集（字典键）
DATASET = "cn_equity.daily_bar"

#: provider 枚举（与字典一致）
PROVIDERS = frozenset({"tushare", "baostock", "wind", "akshare", "fuyao"})

#: A 股收盘 15:00（Asia/Shanghai）= 07:00 UTC
_CLOSE_UTC = time(7, 0)

#: 参与修订比对的数值字段
_VALUE_FIELDS = ("open", "high", "low", "close", "volume", "amount")


def _knowledge_time(trade_date: date) -> datetime:
    """交易日知识时间（naive UTC：15:00 CST 收盘时刻）。"""
    return datetime.combine(trade_date, _CLOSE_UTC)


@lru_cache(maxsize=1)
def _daily_bar_table():
    """目标表（进程内缓存：build_metadata 解析字典开销较大）。"""
    metadata, _specs = build_metadata()
    return metadata.tables[DATASET]


@dataclass(frozen=True, slots=True)
class SyncResult:
    dataset: str
    code: str
    entity_id: int
    window_start: date
    window_end: date
    fetched: int
    rows_written: int
    provider: str


def _resolve_provider(frame: pd.DataFrame, source: Any) -> str:
    raw = frame.attrs.get("source")
    provider = str(raw if raw is not None else (source or "")).lower()
    if provider not in PROVIDERS:
        raise ValueError(f"无法识别 provider: {provider!r}（期望 {sorted(PROVIDERS)}）")
    return provider


def _same_values(prior: Any, record: dict[str, Any]) -> bool:
    for field in _VALUE_FIELDS:
        left, right = prior[field], record[field]
        if left is None and right is None:
            continue
        if left is None or right is None:
            return False
        if not math.isclose(float(left), float(right), rel_tol=1e-9, abs_tol=1e-6):
            return False
    return True


def _latest_rows(
    connection: Any, table: Any, *, entity_id: int, start: date, end: date
) -> dict[date, Any]:
    """窗口内每个交易日的当前最新版本行。"""
    rows = connection.execute(
        select(
            table.c.trade_date,
            table.c.knowledge_time,
            table.c.version,
            *(table.c[name] for name in _VALUE_FIELDS),
        ).where(
            table.c.entity_id == entity_id,
            table.c.trade_date >= start,
            table.c.trade_date <= end,
        )
    ).mappings().all()
    latest: dict[date, Any] = {}
    for row in rows:
        key = row["trade_date"]
        current = latest.get(key)
        if current is None or (
            row["knowledge_time"],
            row["version"],
        ) > (
            current["knowledge_time"],
            current["version"],
        ):
            latest[key] = row
    return latest


def sync_daily_bar(
    engine: Engine,
    hub: Any,
    *,
    code: str,
    start: date | str,
    end: date | str,
    source: Any = None,
    entity_type: str = "equity",
    name: str = "",
    market: str = "cn",
) -> SyncResult:
    """单标的日线同步：首版幂等写入；源值变化时追加修订版本。"""
    window_start = to_date(start)
    window_end = to_date(end)
    if window_start is None or window_end is None:
        raise ValueError(f"窗口非法: start={start!r}, end={end!r}")

    entity = EntityStore(engine).ensure_entity(
        code=code, entity_type=entity_type, name=name, market=market
    )
    frame = hub.get_bars(
        [code],
        start=window_start.isoformat(),
        end=window_end.isoformat(),
        adjust=None,  # 最小切片：不复权原始价
        source=source,
    )
    provider = _resolve_provider(frame, source)
    table = _daily_bar_table()

    now = utcnow()
    rows: list[dict[str, Any]] = []
    with engine.begin() as connection:
        latest = _latest_rows(
            connection,
            table,
            entity_id=entity.entity_id,
            start=window_start,
            end=window_end,
        )
        for item in frame.to_dict("records"):
            trade_date = to_date(item.get("date"))
            if trade_date is None:
                continue
            record: dict[str, Any] = {
                "entity_id": entity.entity_id,
                "trade_date": trade_date,
                "open": item.get("open"),
                "high": item.get("high"),
                "low": item.get("low"),
                "close": item.get("close"),
                "volume": item.get("volume"),
                "amount": item.get("amount"),
                "publish_time": None,
                "ingest_time": now,
                "provider": provider,
            }
            prior = latest.get(trade_date)
            if prior is None:
                record["knowledge_time"] = _knowledge_time(trade_date)
                record["version"] = 1
            elif _same_values(prior, record):
                continue  # 与最新版本一致：无修订
            else:
                record["knowledge_time"] = now  # 重述：修订入库时刻可见
                record["version"] = int(prior["version"]) + 1
            rows.append(record)
        written = append_rows(connection, table, rows)
    return SyncResult(
        dataset=DATASET,
        code=code,
        entity_id=entity.entity_id,
        window_start=window_start,
        window_end=window_end,
        fetched=len(frame.index),
        rows_written=written,
        provider=provider,
    )
