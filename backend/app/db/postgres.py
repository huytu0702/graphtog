"""
PostgreSQL database connection and session management
"""

import logging
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


# SQLAlchemy Base class for all models
class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models"""

    pass


# Get settings
settings = get_settings()
logger = logging.getLogger(__name__)

# Create database engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.SQLALCHEMY_ECHO,
    pool_pre_ping=True,  # Check if connection is alive before using
    pool_size=10,
    max_overflow=20,
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    Use this in FastAPI endpoints with Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database by creating all tables"""
    # Import all models to register them with the Base
    from app.models.document import Document  # noqa: F401
    from app.models.embedding import TextEmbedding  # noqa: F401
    from app.models.query import Query  # noqa: F401
    from app.models.user import User  # noqa: F401

    # Ensure pgvector extension is available
    with engine.connect() as connection:
        try:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            connection.commit()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("pgvector extension initialization failed: %s", exc)

    # Create all tables
    Base.metadata.create_all(bind=engine)


# Event listener for connection pool to ensure proper handling
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable foreign keys for SQLite if used"""
    pass  # Not needed for PostgreSQL
