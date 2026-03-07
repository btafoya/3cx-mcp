"""
PostgreSQL connection pool and query execution.

Uses asyncpg for high-performance async database access.
"""
import asyncpg
from contextlib import asynccontextmanager
from typing import Any, Optional, List

from ..config import DatabaseConfig


class DatabaseError(Exception):
    """Base database error."""
    pass


class ConnectionError(DatabaseError):
    """Failed to connect to database."""
    pass


class QueryError(DatabaseError):
    """Query execution failed."""
    def __init__(self, query: str, cause: Exception):
        self.query = query
        self.cause = cause
        super().__init__(f"Query failed: {cause}")


class DatabasePool:
    """PostgreSQL connection pool."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._pool: Optional[asyncpg.Pool] = None

    async def initialize(self) -> None:
        """Initialize connection pool."""
        if self.config.use_socket:
            dsn = f"user={self.config.user} dbname={self.config.database} host={self.config.socket_dir}"
        else:
            dsn = (
                f"postgresql://{self.config.user}:{self.config.password}"
                f"@{self.config.host}:{self.config.port}/{self.config.database}"
            )

        try:
            self._pool = await asyncpg.create_pool(
                dsn,
                min_size=1,
                max_size=self.config.pool_size,
                command_timeout=30,
            )
        except Exception as e:
            raise ConnectionError(f"Failed to create pool: {e}")

    async def close(self) -> None:
        """Close all connections."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    @asynccontextmanager
    async def connection(self):
        """Get a connection from the pool."""
        if not self._pool:
            await self.initialize()
        async with self._pool.acquire() as conn:
            yield conn

    @asynccontextmanager
    async def transaction(self):
        """Get a connection with an active transaction."""
        async with self.connection() as conn:
            async with conn.transaction():
                yield conn

    async def execute(self, query: str, *args, **kwargs) -> str:
        """Execute a query and return the status."""
        async with self.connection() as conn:
            try:
                return await conn.execute(query, *args, **kwargs)
            except Exception as e:
                raise QueryError(query, e)

    async def fetch(self, query: str, *args, **kwargs) -> List[dict]:
        """Execute a query and return results as list of dicts."""
        async with self.connection() as conn:
            try:
                rows = await conn.fetch(query, *args, **kwargs)
                return [dict(row) for row in rows]
            except Exception as e:
                raise QueryError(query, e)

    async def fetchone(self, query: str, *args, **kwargs) -> Optional[dict]:
        """Execute a query and return first result as dict."""
        results = await self.fetch(query, *args, **kwargs)
        return results[0] if results else None

    async def fetchval(self, query: str, *args, **kwargs) -> Any:
        """Execute a query and return single value."""
        async with self.connection() as conn:
            try:
                return await conn.fetchval(query, *args, **kwargs)
            except Exception as e:
                raise QueryError(query, e)