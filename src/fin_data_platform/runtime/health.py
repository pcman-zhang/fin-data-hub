"""Runtime 健康与就绪检查（doc-20 §8）。"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, text

from fin_data_platform.dictionary import validate_directory
from fin_data_platform.storage.migrations import (
    current_revision,
    expected_head_revision,
)


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    ok: bool
    checks: dict[str, bool]
    errors: list[str]


def check_database(engine: Engine) -> tuple[bool, str | None]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, None
    except Exception as exc:
        return False, f"数据库不可达: {type(exc).__name__}: {exc}"


def check_dictionary() -> tuple[bool, list[str]]:
    errors = validate_directory()
    return (not errors), errors


def check_schema_revision(
    engine: Engine, *, dsn: str | None = None
) -> tuple[bool, str | None]:
    """迁移版本一致性；DB / 脚手架异常均以检查失败返回（不抛出，readiness 需要报告）。"""
    try:
        expected = expected_head_revision(dsn)
        actual = current_revision(engine)
    except Exception as exc:
        return False, f"迁移版本检查失败: {type(exc).__name__}: {exc}"
    if expected and actual != expected:
        return False, f"迁移版本不一致: 库={actual or '无'}，代码={expected}"
    return True, None


def readiness(
    engine: Engine,
    *,
    dsn: str | None = None,
    check_directory: bool = True,
    check_schema: bool = True,
) -> ReadinessReport:
    """就绪检查：数据库连通 / 字典 CI 校验 / 迁移版本一致（fail fast 依据）。"""
    checks: dict[str, bool] = {}
    errors: list[str] = []

    ok_db, db_error = check_database(engine)
    checks["database"] = ok_db
    if db_error:
        errors.append(db_error)

    if check_directory:
        ok_dict, dict_errors = check_dictionary()
        checks["dictionary"] = ok_dict
        errors.extend(dict_errors)

    if check_schema:
        ok_schema, schema_error = check_schema_revision(engine, dsn=dsn)
        checks["schema_revision"] = ok_schema
        if schema_error:
            errors.append(schema_error)

    return ReadinessReport(ok=all(checks.values()), checks=checks, errors=errors)
