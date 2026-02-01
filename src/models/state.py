"""
Workflow state definition for multi-agent system.

Defines the TypedDict schema that tracks requests, agent outputs, routing decisions,
and execution history throughout the multi-agent workflow.
"""

import operator
from typing import (
    TypedDict,
    Optional,
    Literal,
    Annotated
)
from models.io import AnswerSummarizerOutput

class MultiAgentWorkflow(TypedDict):
    """
    State schema for multi-agent workflow execution.
    Tracks user requests, agent outputs, routing decisions, and execution history.
    """

    request: str
    answer: AnswerSummarizerOutput

    # SQL writer artifacts
    sql: Optional[str]
    sql_explanation: Optional[str]

    # Router artifacts
    routing_plan: Optional[str]
    routing_decision: Optional[Literal[str]]
    user_data_file: Optional[str]

    # Insights generator artifacts
    insights: Optional[str]
    queried_data: Optional[str]

    # Tracing fields
    interactions_history: Annotated[list[str], operator.add]
    reasoning_traces: Annotated[list[dict[str, str]], operator.add]
