"""管理 API 入口：``python -m fin_data_platform.api [--host 127.0.0.1] [--port 8000]``。"""

from __future__ import annotations

import argparse
import logging

import uvicorn

from fin_data_platform.api.app import create_app

logger = logging.getLogger("fin_data_platform.api")

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fin-data-platform-api",
        description="FinDataPlatform 管理 API（字典 / 实体 / 任务；doc-14）",
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="绑定地址（默认仅本机）")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="端口")
    parser.add_argument("--log-level", default="info", help="日志级别")
    args = parser.parse_args(argv)

    app = create_app()
    logger.info("管理 API 启动：http://%s:%s（文档 /api/docs）", args.host, args.port)
    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level.lower())
    return 0


if __name__ == "__main__":  # pragma: no cover - 入口
    raise SystemExit(main())
