"""存储配置：读写 DSN 分离（doc-10 §2；只读角色见后续切片）。"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StorageConfig:
    """写入/读取连接配置。

    - ``write_dsn``：内部写入端（按 schema 最小授权）；
    - ``read_dsn``：SDK/读模型只读连接；缺省回退 ``write_dsn``（本地开发）；
    - ``timescale``：是否启用 TimescaleDB 扩展语句（hypertable/压缩）。
    """

    write_dsn: str
    read_dsn: str | None = None
    timescale: bool = True

    @property
    def reader_dsn(self) -> str:
        return self.read_dsn or self.write_dsn

    @classmethod
    def from_env(
        cls,
        *,
        database: str = "fin_data_platform",
        host_override: str | None = None,
        prefix: str = "DATABASE_",
    ) -> StorageConfig:
        """从环境变量构建 DSN（凭证不落盘）。

        ``DATABASE_HOST/PORT/USER/PASSWORD``（``DATABASE_NAME`` 可选）；
        ``host_override`` 用于 DHCP 等地址变动的场景。
        """
        from sqlalchemy.engine import URL

        user = os.environ.get(f"{prefix}USER")
        password = os.environ.get(f"{prefix}PASSWORD")
        host = host_override or os.environ.get(f"{prefix}HOST")
        port = os.environ.get(f"{prefix}PORT", "5432")
        name = os.environ.get(f"{prefix}NAME", database)
        if not (user and password and host):
            raise ValueError(
                f"缺少 {prefix}USER/{prefix}PASSWORD/{prefix}HOST 环境变量"
            )
        url = URL.create(
            "postgresql+psycopg",
            username=user,
            password=password,
            host=host,
            port=int(port),
            database=name,
        )
        return cls(write_dsn=url.render_as_string(hide_password=False))
