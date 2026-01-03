from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncEngine

from configs.config import PostgresSettings


def get_engine_async() -> AsyncEngine:
    return create_async_engine(
        PostgresSettings().pg_connection_str,
        isolation_level="REPEATABLE READ",
        pool_pre_ping=True
        # echo=True
    )


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_engine_async(),
        expire_on_commit=False
    )
