"""Database engine + session factory.

SQLite is tuned for a small concurrent web workload:
- WAL lets readers proceed while a writer commits.
- foreign_keys is OFF by default in SQLite; we turn it on so the schema's
  relationships are actually enforced.
"""
from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str):
    engine = create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})

    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_conn, _):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA busy_timeout=5000")  # wait for a writer instead of failing instantly
            cur.close()

    return engine


engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session (unit of work) per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Bump when models change. There are no migrations: a SQLite file stamped with an
# older version (PRAGMA user_version) is dropped and re-seeded on boot, unless
# RESET_DB_ON_SCHEMA_CHANGE=0 (production), where boot fails loudly instead.
# ponytail: add Alembic once real accounts must survive a schema change.
SCHEMA_VERSION = 7


def rebuild(eng=None) -> None:
    from . import models  # noqa: F401  (register every table on Base.metadata)
    eng = eng or engine
    with eng.begin() as conn:
        Base.metadata.drop_all(conn)
        Base.metadata.create_all(conn)
        if eng.url.get_backend_name() == "sqlite":
            conn.exec_driver_sql(f"PRAGMA user_version = {SCHEMA_VERSION}")


def ensure_schema(eng=None) -> None:
    from . import models  # noqa: F401
    eng = eng or engine
    if eng.url.get_backend_name() != "sqlite":
        Base.metadata.create_all(eng)
        return
    with eng.connect() as conn:
        current = conn.exec_driver_sql("PRAGMA user_version").scalar()
    if current != SCHEMA_VERSION:
        if current and not settings.reset_db_on_schema_change:
            raise RuntimeError(f"Database schema is v{current} but the code expects v{SCHEMA_VERSION}. Migrate it, "
                               "or set RESET_DB_ON_SCHEMA_CHANGE=1 to wipe it and re-seed (deletes every account).")
        rebuild(eng)
