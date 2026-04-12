from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create database if not exists, then create all tables."""
    temp_engine = create_engine(settings.database_url_without_db)
    with temp_engine.connect() as conn:
        conn.execute(
            text(
                f"CREATE DATABASE IF NOT EXISTS `{settings.db_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        )
        conn.commit()
    temp_engine.dispose()

    from app.models import user, task, tool, log, setting, token_usage  # noqa: F401
    from app.models import conversation, emotion, user_profile, ai_identity, memory_summary  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Auto-migrate: add missing columns to existing tables
    _auto_add_missing_columns()


def _auto_add_missing_columns() -> None:
    """Inspect all model tables and ALTER TABLE to add any missing columns."""
    inspector = inspect(engine)
    for table_name, table in Base.metadata.tables.items():
        if not inspector.has_table(table_name):
            continue
        existing_cols = {col["name"] for col in inspector.get_columns(table_name)}
        for col in table.columns:
            if col.name not in existing_cols:
                col_type = col.type.compile(engine.dialect)
                nullable = "NULL" if col.nullable else "NOT NULL"
                default = ""
                if col.default is not None:
                    val = getattr(col.default, "arg", None)
                    if val is not None:
                        default = f" DEFAULT {val!r}"
                    # val 为 None 时不生成 DEFAULT 子句
                ddl = f"ALTER TABLE `{table_name}` ADD COLUMN `{col.name}` {col_type} {nullable}{default}"
                with engine.connect() as conn:
                    conn.execute(text(ddl))
                    conn.commit()
