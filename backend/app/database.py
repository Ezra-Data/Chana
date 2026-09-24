from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


class Base(DeclarativeBase):
    pass


def get_database_url() -> str:
    """Normalize database connection string for SQLAlchemy asyncpg."""
    url = settings.DATABASE_URL
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


db_url = get_database_url()
is_sqlite = "sqlite" in db_url

engine = create_async_engine(
    db_url,
    echo=False,
    connect_args={"check_same_thread": False} if is_sqlite else {},
    pool_pre_ping=True if not is_sqlite else False,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    """Dependency that provides an async database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def _migrate_datetime_columns(conn) -> None:
    """
    Idempotent migration: convert any TIMESTAMP WITHOUT TIME ZONE columns to
    TIMESTAMP WITH TIME ZONE so asyncpg does not raise the
    'can't subtract offset-naive and offset-aware datetimes' error.
    Safe to run repeatedly — it only alters columns still typed WITHOUT TIME ZONE.
    """
    statements = [
        # users
        "ALTER TABLE users ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'",
        # tickets
        "ALTER TABLE tickets ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'",
        "ALTER TABLE tickets ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'",
        "ALTER TABLE tickets ALTER COLUMN first_response_at TYPE TIMESTAMPTZ USING first_response_at AT TIME ZONE 'UTC'",
        "ALTER TABLE tickets ALTER COLUMN resolved_at TYPE TIMESTAMPTZ USING resolved_at AT TIME ZONE 'UTC'",
        "ALTER TABLE tickets ALTER COLUMN rated_at TYPE TIMESTAMPTZ USING rated_at AT TIME ZONE 'UTC'",
        # ticket_messages
        "ALTER TABLE ticket_messages ALTER COLUMN timestamp TYPE TIMESTAMPTZ USING timestamp AT TIME ZONE 'UTC'",
        # chat_sessions
        "ALTER TABLE chat_sessions ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'",
        "ALTER TABLE chat_sessions ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'",
        # chat_messages
        "ALTER TABLE chat_messages ALTER COLUMN timestamp TYPE TIMESTAMPTZ USING timestamp AT TIME ZONE 'UTC'",
        # knowledge_entries
        "ALTER TABLE knowledge_entries ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'",
        "ALTER TABLE knowledge_entries ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'",
        # nav_nodes
        "ALTER TABLE nav_nodes ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'",
    ]
    for sql in statements:
        try:
            await conn.execute(text(sql))
        except Exception:
            # Column may already be TIMESTAMPTZ or table may not exist yet — ignore
            pass


async def init_db():
    """Create all tables on startup automatically (PostgreSQL or SQLite)."""
    # Import all models so Base.metadata is fully populated with all tables
    import app.models.user
    import app.models.ticket
    import app.models.knowledge
    import app.models.navigation
    import app.models.chat

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Convert any legacy timezone-naive timestamp columns on existing databases
        if not is_sqlite:
            await _migrate_datetime_columns(conn)
