from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
import os
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Função para testar conexão com timeout curto
def _test_connection(db_url: str, timeout: int = 5) -> bool:
    """Testa se consegue conectar ao banco de dados."""
    try:
        if db_url.startswith("mssql"):
            test_connect_args = {
                "timeout": timeout,
                "login_timeout": timeout,
                "autocommit": True
            }
        elif db_url.startswith("sqlite"):
            test_connect_args = {"check_same_thread": False, "timeout": timeout}
        else:
            test_connect_args = {}
        
        test_engine = create_engine(
            db_url,
            connect_args=test_connect_args,
            pool_pre_ping=False
        )
        
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        test_engine.dispose()
        return True
    except Exception as e:
        logger.warning(f"Failed to connect to {db_url.split('@')[-1] if '@' in db_url else 'database'}: {e}")
        return False

# Determinar qual banco usar (com fallback para SQLite em desenvolvimento)
database_url = settings.database_url
use_sqlite_fallback = False

# Se estiver tentando usar Azure SQL, testar conexão primeiro
if database_url.startswith("mssql"):
    logger.info("Testing Azure SQL connection...")
    if not _test_connection(database_url, timeout=5):
        # Fallback para SQLite em desenvolvimento
        sqlite_path = os.getenv("SQLITE_FALLBACK_PATH", "/app/data/app.db")
        database_url = f"sqlite:///{sqlite_path}"
        use_sqlite_fallback = True
        logger.warning(f"⚠️  Azure SQL not accessible. Using SQLite fallback: {database_url}")
    else:
        logger.info("✓ Azure SQL connection successful")

# Configurar connect_args baseado no tipo de banco
if database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False, "timeout": 30}
elif database_url.startswith("mssql"):
    connect_args = {
        "timeout": 120,
        "login_timeout": 120,
        "autocommit": True
    }
else:
    connect_args = {}

# Pool settings específicos para SQL Server
if database_url.startswith("mssql"):
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args=connect_args,
        pool_timeout=60,
        pool_recycle=3600
    )
else:
    engine = create_engine(
        database_url, 
        pool_pre_ping=True, 
        connect_args=connect_args
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Log qual banco está sendo usado
if use_sqlite_fallback:
    logger.warning(f"🔄 Running with SQLite fallback (Azure SQL not accessible)")
else:
    db_type = "SQLite" if database_url.startswith("sqlite") else "Azure SQL" if database_url.startswith("mssql") else "Database"
    logger.info(f"✓ Using {db_type}")

# Enable WAL mode for SQLite databases to improve concurrency. This PRAGMA persists
# in the DB file, but we set it on each new connection to be safe.
if database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, connection_record):  # pragma: no cover
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL;")
        finally:
            cursor.close()
