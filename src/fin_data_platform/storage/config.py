"""存储配置：读写 DSN 分离（doc-10 §2；只读角色见后续切片）。"""

from __future__ import annotations

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
