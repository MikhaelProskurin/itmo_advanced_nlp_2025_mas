"""
Input/output Pydantic models for agent communications.

Defines structured schemas for agent outputs (router, SQL writer, insight generator,
answer summarizer) and tool inputs (database search, data reading).
"""

from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel, Field

class TechnicalMixin(BaseModel):
    """Base mixin for agent outputs with reasoning and debugging fields."""

    reasoning: Optional[str] = Field(description="Reasoning behind the decision")
    failure_reason: Optional[str] = Field(description="Reason for failure when you said 'I don't know'")
    tool_calls: Optional[Dict[str, Any]] = Field(description="Tool calls made during the process")

class RouterOutput(TechnicalMixin):
    """Router agent output with routing decision and plan."""

    routing_decision: Literal["sql_writer", "insight_generator", "answer_summarizer", "general_question"]
    routing_plan: Optional[str] = Field(description="The step-by-step plan of agent calls to solve the problem.")
    user_data_file: Optional[str] = Field(description="The data file path on the operating system user requests to analyze.")

class SQLWriterOutput(TechnicalMixin):
    """SQL writer agent output with query and explanation."""

    sql: Optional[str] = Field(description="Generated SQL query")
    sql_explanation: Optional[str] = Field(description="Explanation of the SQL query")

class InsightGeneratorOutput(TechnicalMixin):
    """Insight generator agent output with data and analysis results."""

    queried_data: Optional[list] = Field(description="Data queried from the database")
    insights: Optional[str] = Field(description="Insights found from the data")
    sql: Optional[str] = Field(description="SQL query for the database search")

class AnswerSummarizerOutput(TechnicalMixin):
    """Answer summarizer agent output with final response."""

    answer: Optional[str] = Field(description="Answer to the question")

class DatabaseSearchTool(BaseModel):
    """Tool schema for database search operations."""

    statement: str = Field(description="SQL statement to search the database")

class ReadDataTool(BaseModel):
    """Tool schema for reading data files."""

    path: str = Field(description="Path to the data file")
