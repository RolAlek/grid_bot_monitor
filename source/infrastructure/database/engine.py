from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from source.settings import get_settings


settings = get_settings()

engine: AsyncEngine = create_async_engine(
    url=settings.database.connection_url,
    echo=settings.database.db_echo,
    pool_size=settings.database.db_pool_size,
    max_overflow=settings.database.db_max_overflow,
    pool_pre_ping=True,
)
async_session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)
