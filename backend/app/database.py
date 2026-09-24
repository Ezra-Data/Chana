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
    Queries information_schema so it only alters columns that actually need it,
    preventing PostgreSQL aborted-transaction errors.
    """
    try:
        query = text("""
            SELECT table_name, column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
              AND data_type = 'timestamp without time zone';
        """)
        result = await conn.execute(query)
        columns_to_alter = result.fetchall()
        for table_name, column_name in columns_to_alter:
            alter_sql = text(
                f'ALTER TABLE "{table_name}" ALTER COLUMN "{column_name}" '
                f'TYPE TIMESTAMPTZ USING "{column_name}" AT TIME ZONE \'UTC\''
            )
            await conn.execute(alter_sql)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Note during datetime migration check: {e}")


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
