from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


_MANAGED_TABLES = (
    "biz_system_logs",
    "biz_task_results",
    "biz_task_model_calls",
    "biz_task_status_history",
    "biz_tasks",
    "biz_material_assets",
)

_SCHEMA_SIGNATURE = {
    "biz_tasks": {"id", "task_id", "status", "progress", "source_primary_asset_id", "source_file_name", "create_time", "update_time", "is_deleted", "remark"},
    "biz_task_status_history": {"id", "task_status_history_id", "task_id", "previous_status", "current_status", "change_time", "create_time", "update_time", "is_deleted", "remark"},
    "biz_task_model_calls": {"id", "task_model_call_id", "task_id", "provider", "model_name", "operation", "response_status_code", "request_payload_json", "response_payload_json", "create_time", "update_time", "is_deleted", "remark"},
    "biz_task_results": {"id", "task_result_id", "task_id", "clip_index", "material_asset_id", "create_time", "update_time", "is_deleted", "remark"},
    "biz_system_logs": {"id", "system_log_id", "level", "stage", "event", "create_time", "update_time", "is_deleted", "remark"},
    "biz_material_assets": {"id", "material_asset_id", "task_id", "source_material_id", "asset_role", "local_storage_path", "create_time", "update_time", "is_deleted", "remark"},
}


def create_sqlalchemy_engine(database_url: str, echo: bool = False):
    connect_args: dict[str, object] = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(
        database_url,
        echo=echo,
        future=True,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


def build_sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def build_session_factory(engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_database(engine) -> None:
    import ai_cut_db.models as models  # noqa: F401

    if _requires_schema_rebuild(engine):
        _rebuild_managed_tables(engine)
    Base.metadata.create_all(bind=engine)
    _drop_legacy_tables(engine)


def _requires_schema_rebuild(engine) -> bool:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    for table_name, required_columns in _SCHEMA_SIGNATURE.items():
        if table_name not in table_names:
            continue
        existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
        if not required_columns.issubset(existing_columns):
            return True
    return False


def _rebuild_managed_tables(engine) -> None:
    with engine.begin() as conn:
        if engine.dialect.name == "mysql":
            conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 0")
        try:
            for table_name in _MANAGED_TABLES:
                conn.exec_driver_sql(f"DROP TABLE IF EXISTS {table_name}")
        finally:
            if engine.dialect.name == "mysql":
                conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 1")


def _drop_legacy_tables(engine) -> None:
    # Drop all obsolete tables to ensure runtime only uses the task-centric 6-table schema.
    legacy_tables = (
        "biz_source_assets",
        "biz_task_sources",
        "biz_task_outputs",
        "biz_video_model_usage",
        "biz_agent_events",
        "biz_agent_artifacts",
        "biz_agent_runs",
        "biz_agent_definitions",
        "task_outputs",
        "task_source_assets",
        "tasks",
        "source_assets",
        "video_model_usage",
        "agent_events",
        "agent_artifacts",
        "agent_runs",
        "agent_definitions",
    )
    with engine.begin() as conn:
        for table_name in legacy_tables:
            conn.exec_driver_sql(f"DROP TABLE IF EXISTS {table_name}")
