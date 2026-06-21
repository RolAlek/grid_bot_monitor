from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from source.settings import get_settings


settings = get_settings()

engine: AsyncEngine = create_async_engine(
    url=settings.database.url,
    echo=settings.database.echo,
)
async_session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)
