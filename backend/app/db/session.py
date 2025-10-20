from sqlalchemy import create_engine, event, text, pool
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, NullPool
import os
import logging
from typing import Dict, Any

from app.core.config import settings

logger = logging.getLogger(__name__)


def _test_connection(db_url: str, timeout: int = 5) -> bool:
    """Test database connection with timeout"""
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
            pool_pre_ping=False,
            poolclass=NullPool  # Don't pool for test
        )

        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        test_engine.dispose()
        return True
    except Exception as e:
        logger.warning(f"Failed to connect to {db_url.split('@')[-1] if '@' in db_url else 'database'}: {e}")
        return False


def get_engine_config() -> Dict[str, Any]:
    """Get optimized engine configuration based on database type and environment"""
    database_url = settings.database_url
    use_sqlite_fallback = False

    # Test Azure SQL connection if specified
    if database_url.startswith("mssql"):
        logger.info("Testing Azure SQL connection...")
        if not _test_connection(database_url, timeout=5):
            if not settings.is_production:
                # Fallback to SQLite in development
                sqlite_path = os.getenv("SQLITE_FALLBACK_PATH", "/app/data/app.db")
                database_url = f"sqlite:///{sqlite_path}"
                use_sqlite_fallback = True
                logger.warning(f"⚠️  Azure SQL not accessible. Using SQLite fallback: {database_url}")
            else:
                raise ConnectionError("Azure SQL connection failed in production")
        else:
            logger.info("✓ Azure SQL connection successful")

    # Configure connect_args based on database type
    if database_url.startswith("sqlite"):
        connect_args = {
            "check_same_thread": False,
            "timeout": 30,
        }
        # Use NullPool for SQLite to avoid threading issues
        poolclass = NullPool if settings.is_production else QueuePool
        pool_config = {} if settings.is_production else {
            "pool_size": 5,
            "max_overflow": 10,
            "pool_timeout": 30,
        }
    elif database_url.startswith("mssql"):
        connect_args = {
            "timeout": 120,
            "login_timeout": 120,
            "autocommit": False,  # Let SQLAlchemy manage transactions
        }
        poolclass = QueuePool
        pool_config = {
            "pool_size": settings.db_pool_size,
            "max_overflow": settings.db_max_overflow,
            "pool_timeout": settings.db_pool_timeout,
            "pool_recycle": settings.db_pool_recycle,
            "pool_pre_ping": True,
        }
    elif database_url.startswith("postgresql"):
        connect_args = {
            "connect_timeout": 10,
        }
        poolclass = QueuePool
        pool_config = {
            "pool_size": settings.db_pool_size,
            "max_overflow": settings.db_max_overflow,
            "pool_timeout": settings.db_pool_timeout,
            "pool_recycle": settings.db_pool_recycle,
            "pool_pre_ping": True,
        }
    else:
        connect_args = {}
        poolclass = QueuePool
        pool_config = {
            "pool_size": settings.db_pool_size,
            "max_overflow": settings.db_max_overflow,
        }

    engine_config = {
        "url": database_url,
        "connect_args": connect_args,
        "poolclass": poolclass,
        "echo": settings.db_echo,
        **pool_config,
    }

    # Log configuration
    if use_sqlite_fallback:
        logger.warning("🔄 Running with SQLite fallback (Azure SQL not accessible)")
    else:
        db_type = "SQLite" if database_url.startswith("sqlite") else \
                  "Azure SQL" if database_url.startswith("mssql") else \
                  "PostgreSQL" if database_url.startswith("postgresql") else "Database"
        logger.info(f"✓ Using {db_type}")
        logger.info(f"Connection pool: size={pool_config.get('pool_size', 'N/A')}, "
                   f"overflow={pool_config.get('max_overflow', 'N/A')}")

    return engine_config


# Create engine with optimized configuration
engine_config = get_engine_config()
engine = create_engine(**engine_config)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Avoid lazy loading errors after commit
)


# Enable WAL mode for SQLite databases to improve concurrency
if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")  # Better performance
            cursor.execute("PRAGMA cache_size=-64000;")  # 64MB cache
            cursor.execute("PRAGMA temp_store=MEMORY;")
            logger.debug("SQLite optimizations applied")
        except Exception as e:
            logger.warning(f"Failed to apply SQLite optimizations: {e}")
        finally:
            cursor.close()


# Log database pool events in development
if settings.is_development:
    @event.listens_for(engine, "connect")
    def _log_connection(dbapi_conn, conn_record):
        logger.debug("Database connection established")

    @event.listens_for(engine, "close")
    def _log_close(dbapi_conn, conn_record):
        logger.debug("Database connection closed")


# Dependency for FastAPI routes
def get_db():
    """Database session dependency for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
