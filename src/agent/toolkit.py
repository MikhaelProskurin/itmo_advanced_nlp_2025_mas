"""
Utility tools and helper functions for agent operations.

Provides database search tools, data reading utilities, chain execution
with fallback support, and database snapshot upload functionality.
"""

import os
from dotenv import load_dotenv, find_dotenv

import pandas as pd

from typing import Sequence
from pydantic import BaseModel
from sqlalchemy import Row

from langchain.tools import tool
from langchain_core.runnables import Runnable
from langchain_core.exceptions import OutputParserException

from database.manager import PostgresAlchemyManager
from models.io import DatabaseSearchTool, ReadDataTool

@tool("search_postgres_database", args_schema=DatabaseSearchTool)
async def search_postgres_database(statement: str) -> Sequence[Row]:
    """Execute SQL statement against PostgreSQL database.

    Args:
        statement: SQL statement to execute.

    Returns:
        Query results as sequence of database rows.
    """

    load_dotenv(find_dotenv())
    manager = PostgresAlchemyManager(postgres_dsn=os.getenv("POSTGRES_DSN"))
    return await manager.execute_sql_statement(statement.strip())

@tool("read_provided_data", args_schema=ReadDataTool)
def read_provided_data(path: str = ".data/") -> list[dict]:
    """Load data from CSV file.

    Args:
        path: Path to the CSV file.

    Returns:
        List of dictionaries representing CSV rows.
    """
    dataframe: pd.DataFrame = pd.read_csv(path)
    return dataframe.to_dict("records")

async def with_fallback(
    chain: Runnable,
    fallback_chain: Runnable,
    invocation_kwargs: dict,
    n_retries: int = 3
) -> BaseModel:
    """Execute chain with fallback on parsing failure.

    Args:
        chain: Primary chain to execute.
        fallback_chain: Fallback chain used when primary fails.
        invocation_kwargs: Arguments to pass to chains.
        n_retries: Number of retry attempts.

    Returns:
        Parsed model output from chain execution.
    """

    for attempt in range(n_retries):
        try:
            return await chain.ainvoke(invocation_kwargs)
        except OutputParserException:
            result = await fallback_chain.ainvoke(invocation_kwargs)

        return result
    else:
        raise OutputParserException

def upload_database_snapshot(
    database_manager: PostgresAlchemyManager,
    snapshot_tables_path: str = "./data",
    format: str = ".csv"
) -> None:
    """Upload CSV files from directory to database tables.

    Args:
        database_manager: Database manager instance.
        snapshot_tables_path: Directory containing CSV snapshot files.
        format: File format extension to process.
    """
    for path in os.listdir(snapshot_tables_path):
        if path.endswith(format):

            print(f"Uploading table under: {path}")

            database_manager.copy_from_csv(
                csv_path=snapshot_tables_path + "/" + path,
                table=path.split(".")[0]
            )
    print("Snapshot uploaded successfully!")
