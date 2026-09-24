from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
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
