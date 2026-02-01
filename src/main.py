"""
Application entry point for coffee shop analyst assistant.

Initializes database manager, language model, and multi-agent system,
then starts an interactive session for analytical queries.
"""

import os
import asyncio

from dotenv import load_dotenv, find_dotenv

from langchain_openai import ChatOpenAI

from database.schemas import meta
from database.manager import PostgresAlchemyManager
from agent.mas import (
    CoffeeShopAnalystAsistant,
    provide_agentic_session
)

MODEL_NAME: str = "qwen3-32b"

async def main():
    """Initialize and run the coffee shop analyst agent session."""

    load_dotenv(find_dotenv())

    database_manager = PostgresAlchemyManager(
        postgres_dsn=os.getenv("POSTGRES_DSN"),
        metadata=meta
    )
    llm = ChatOpenAI(
        base_url=os.getenv("BASE_URL"),
        api_key=os.getenv("LLM_API_KEY"),
        model=os.getenv("MODEL_NAME") or MODEL_NAME
    )
    agent = CoffeeShopAnalystAsistant(
        llm=llm,
        database_manager=database_manager,
        max_interactions_count=5,
        fallback_temperature=0.3
    )

    await provide_agentic_session(agent=agent)

if __name__ == "__main__":
    asyncio.run(main())
