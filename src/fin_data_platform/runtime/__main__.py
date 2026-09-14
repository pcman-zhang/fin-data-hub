"""FinDataRuntime 入口：``python -m fin_data_platform.runtime --role all|scheduler|worker``。

角色可拆进程（doc-20 §3.2）：``scheduler`` 只做调度与分发，``worker`` 只做执行，
两者仅凭 PostgreSQL 协调；``all`` 为单机默认。

同步任务由环境变量装配（TASK-3.6 切片 3）：
``FDP_SYNC_CODES`` / ``FDP_SYNC_START`` / ``FDP_SYNC_SOURCE`` / ``FDP_SYNC_SCHEDULE``；
未配置时启动为空 Runtime（仅控制面）。
"""

from __future__ import annotations

import argparse
import logging
import signal
import threading

from fin_data_platform.ingestion.bootstrap import build_sync_runtime
from fin_data_platform.ingestion.settings import SyncSettings
from fin_data_platform.runtime.app import RuntimeApp, default_registry
from fin_data_platform.runtime.config import ROLES, RuntimeConfig
from fin_data_platform.storage.engine import create_write_engine

logger = logging.getLogger("fin_data_platform.runtime")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fin-data-platform-runtime",
        description="FinDataRuntime（控制面进程；doc-20）",
    )
    parser.add_argument("--role", choices=ROLES, default="all", help="进程角色")
    parser.add_argument("--workers", type=int, default=2, help="WorkerPool 线程数")
    parser.add_argument("--log-level", default="INFO", help="日志级别")
    parser.add_argument(
        "--check",
        action="store_true",
        help="仅执行就绪检查后退出（0 通过 / 1 未通过；供容器健康检查）",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    try:
        settings = SyncSettings.from_env()
    except ValueError as exc:
        logger.error("同步配置非法: %s", exc)
        return 2

    config = RuntimeConfig.from_env(role=args.role, worker_count=args.workers)
    if settings is not None:
        app = build_sync_runtime(config, settings)
        logger.info(
            "同步任务装配：codes=%s source=%s schedule=%s start=%s",
            ",".join(settings.codes),
            settings.source or "auto",
            settings.schedule or "manual",
            settings.start.isoformat(),
        )
    else:
        engine = create_write_engine(config.storage)
        app = RuntimeApp(config, engine=engine, registry=default_registry())

    report = app.readiness()
    if report is not None and not report.ok:
        logger.error("readiness 未通过: %s", "; ".join(report.errors))
        return 1
    if args.check:
        logger.info("就绪检查通过（--check）")
        return 0

    stop = threading.Event()

    def _handle(signum: int, _frame: object) -> None:
        logger.info("收到信号 %s，准备停止", signum)
        stop.set()

    signal.signal(signal.SIGINT, _handle)
    signal.signal(signal.SIGTERM, _handle)

    app.start()
    logger.info("FinDataRuntime 已启动（role=%s）", config.role)
    try:
        while not stop.wait(1.0):
            pass
    finally:
        app.stop()
        logger.info("FinDataRuntime 已停止")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
