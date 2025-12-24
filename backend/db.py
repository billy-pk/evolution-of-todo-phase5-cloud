from sqlmodel import create_engine, Session
from typing import Generator
from config import settings

# Create the database engine with Neon-optimized settings
# Neon is a serverless PostgreSQL provider that requires:
# - Short-lived connections (pool_pre_ping to check connection health)
# - Aggressive connection recycling (pool_recycle)
# - Smaller pool sizes for serverless environments
# NOTE: Neon pooled connections don't support statement_timeout in options
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_POOL_MAX_OVERFLOW,
    pool_pre_ping=True,  # Verify connections before using them
    pool_recycle=300,    # Recycle connections every 5 minutes
    connect_args={
        "connect_timeout": 10
    },
    echo=False  # Set to True for SQL query logging
)


def get_session() -> Generator[Session, None, None]:
    """
    Dependency to get a database session.
    """
    with Session(engine) as session:
        yield session