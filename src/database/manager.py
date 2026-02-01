"""
PostgreSQL database management using SQLAlchemy.

Provides async and sync database operations including table management,
SQL execution, CSV data import, and ORM object persistence.
"""

import pandas as pd

from typing import Sequence

from sqlalchemy import (
    text,
    create_engine,
    MetaData,
    Table,
    Row,
    Engine
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker
)

class PostgresAlchemyManager:
    """Manager for PostgreSQL database operations using SQLAlchemy.

    Provides both async and sync database connections for various operations.
    """

    def __init__(self, postgres_dsn: str, metadata: MetaData = None) -> None:
        """Initialize database manager with connection engines.

        Args:
            postgres_dsn: PostgreSQL connection string (asyncpg format).
            metadata: SQLAlchemy metadata containing table definitions.
        """

        self.engine: AsyncEngine = create_async_engine(url=postgres_dsn)
        self.session_factory = async_sessionmaker[AsyncSession](bind=self.engine)
        self.meta = metadata

        # Initialize sync engine for sync operations
        sync_dsn = postgres_dsn.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        self.sync_engine: Engine = create_engine(url=sync_dsn)

    @property
    def database_model(self) -> list[Table]:
        """Get sorted list of database tables from metadata.

        Returns:
            List of SQLAlchemy Table objects sorted by dependencies.
        """
        return self.meta.sorted_tables

    async def create_database_structure(self) -> None:
        """Create all database tables defined in metadata."""
        async with self.engine.begin() as conn:
            return await conn.run_sync(self.meta.create_all)

    async def drop_database_structure(self) -> None:
        """Drop all database tables defined in metadata."""
        async with self.engine.begin() as conn:
            return await conn.run_sync(self.meta.drop_all)

    async def execute_sql_statement(self, sql: str) -> Sequence[Row]:
        """Execute raw SQL statement and return results.

        Args:
            sql: SQL statement to execute.

        Returns:
            Sequence of result rows.
        """
        async with self.session_factory() as s:
            result = await s.execute(text(sql))
            return result.fetchall()

    def copy_from_csv(self, csv_path: str, table: str, chunksize: int = 10000) -> None:
        """Load CSV data into database table.

        Args:
            csv_path: Path to CSV file.
            table: Target table name.
            chunksize: Number of rows per batch insert.
        """
        dataframe: pd.DataFrame = pd.read_csv(csv_path)

        with self.sync_engine.begin() as conn:
            dataframe.to_sql(
                name=table,
                con=conn,
                if_exists="fail",
                index=False,
                chunksize=chunksize
            )
            conn.commit()

    async def dump_object(self, orm_model: DeclarativeBase) -> None:
        """Persist ORM model object to database.

        Args:
            orm_model: SQLAlchemy model instance to save.
        """
        async with self.session_factory() as s:
            s.add(orm_model)
            await s.commit()
