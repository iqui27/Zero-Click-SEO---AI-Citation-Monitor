from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Configurar connect_args baseado no tipo de banco
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False, "timeout": 30}
elif settings.database_url.startswith("mssql"):
    connect_args = {
        "timeout": 120,
        "login_timeout": 120,
        "autocommit": True
    }
else:
    connect_args = {}

# Pool settings específicos para SQL Server
if settings.database_url.startswith("mssql"):
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        connect_args=connect_args,
        pool_timeout=60,
        pool_recycle=3600
    )
else:
    engine = create_engine(
        settings.database_url, 
        pool_pre_ping=True, 
        connect_args=connect_args
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Enable WAL mode for SQLite databases to improve concurrency. This PRAGMA persists
# in the DB file, but we set it on each new connection to be safe.
if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, connection_record):  # pragma: no cover
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL;")
        finally:
            cursor.close()
