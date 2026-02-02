"""
Multi-agent system for coffee shop data analysis.

Implements a coordinated workflow of specialized agents (router, SQL writer,
insight generator, answer summarizer) to handle analytical queries about
coffee shop operations and database.
"""

import uuid
from typing import Literal

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from models.io import (
    RouterOutput,
    SQLWriterOutput,
    InsightGeneratorOutput,
    AnswerSummarizerOutput,
)
from models.state import MultiAgentWorkflow
from models.prompts import meta_prompts_store
from database.manager import PostgresAlchemyManager
from database.schemas import SessionTracing
from agent.toolkit import (
    search_postgres_database,
    read_provided_data,
    with_fallback
)

class CoffeeShopAnalystAsistant:
    """
    Multi-agent system for coffee shop data analysis and SQL query generation.

    Coordinates multiple specialized agents (router, SQL writer, insight generator, answer summarizer)
    to handle user requests about coffee shop database analytics.
    """

    def __init__(self,
        llm: ChatOpenAI,
        database_manager: PostgresAlchemyManager,
        max_interactions_count: int = 5,
        fallback_temperature: float = 0.3
    ) -> None:
        """Initialize the coffee shop analyst assistant.

        Args:
            llm: Language model for agent interactions.
            database_manager: Manager for PostgreSQL database operations.
            max_interactions_count: Maximum number of agent interactions before forcing summarization.
            fallback_temperature: Temperature setting for fallback LLM when parsing fails.
        """

        self.llm = llm
        self.prompts = meta_prompts_store
        self.graph = StateGraph(MultiAgentWorkflow)
        self.max_interactions_count = max_interactions_count
        self.database_manager = database_manager

        # Providing access for tools
        toolkit = [search_postgres_database, read_provided_data]
        self.tools = {_tool.name: _tool for _tool in toolkit}

        # Setting up fallback LLM with increased 'temperature'
        self.fallback_llm = self.llm.with_config(
            RunnableConfig(configurable={"temperature": fallback_temperature})
        )

    @property
    def compiled_graph(self) -> CompiledStateGraph:
        """Build and compile the agent workflow graph.

        Returns:
            Compiled state graph ready for execution.
        """

        self.graph.add_node("router_node", self.router_node, defer=True)
        self.graph.add_node("sql_writer_node", self.sql_writer_node)
        self.graph.add_node("insight_generator_node", self.insight_generator_node)
        self.graph.add_node("answer_summarizer_node", self.answer_summarizer_node)
        self.graph.add_node("simple_qa_node", self.simple_qa_node)

        self.graph.add_edge(START, "router_node")
        self.graph.add_conditional_edges(
            "router_node",
            self.routing_gate,
            {
                "sql_writer": "sql_writer_node",
                "insight_generator": "insight_generator_node",
                "answer_summarizer": "answer_summarizer_node",
                "general_question": "simple_qa_node"
            }
        )
        self.graph.add_edge("sql_writer_node", "router_node")
        self.graph.add_edge("insight_generator_node", "router_node")
        self.graph.add_edge("answer_summarizer_node", END)
        self.graph.add_edge("simple_qa_node", END)

        return self.graph.compile()

    def routing_gate(self, state: MultiAgentWorkflow) -> Literal[str]:
        """Determine next agent to route to based on workflow state."""

        history = state.get("interactions_history", [])

        if len(history) >= self.max_interactions_count:
            return "answer_summarizer"

        if history and state["routing_decision"] == history[-1]:
            return "answer_summarizer"

        print(f"Routing decision: {state['routing_decision']}")

        return state["routing_decision"]

    async def simple_qa_node(self, state: MultiAgentWorkflow) -> MultiAgentWorkflow:
        """Answers questions that are too simple or behind the system's scope."""

        node_propmpt = ChatPromptTemplate.from_messages([
            ("system", self.prompts.simple_qa_prompt),
            ("human", "{request}")
        ])
        chain = node_propmpt | self.llm | StrOutputParser()
        response: str = await chain.ainvoke({"request": state["request"]})

        return {"answer": response}

    async def router_node(self, state: MultiAgentWorkflow) -> MultiAgentWorkflow:
        """Route user request to appropriate specialist agent."""

        na = "Not available yet"

        parser = PydanticOutputParser(pydantic_object=RouterOutput)

        agent_prompt = self.prompts.router_prompt.format(**{
            "fmt": parser.get_format_instructions(),
            "sql": state.get("sql", na),
            "sql_explanation": state.get("sql_explanation", na),
            "insights": state.get("insights", na),
            "interactions_history": state.get("interactions_history", []),
            "routing_plan": state.get("routing_plan", na)
        })
        node_prompt = ChatPromptTemplate.from_messages([
            ("system", "{agent_propmpt}"),
            ("human", "{request}"),
        ])
        response: RouterOutput = await with_fallback(
            node_prompt | self.llm | parser,
            node_prompt | self.fallback_llm | parser,
            {"request": state["request"], "agent_propmpt": agent_prompt}
        )
        update = {
            "routing_decision": response.routing_decision,
            "routing_plan": response.routing_plan,
            "user_provided_path": response.user_data_path,
            "reasoning_traces": [{"reasoning": response.reasoning, "failure_reason": response.failure_reason}]
        }
        return update

    async def sql_writer_node(self, state: MultiAgentWorkflow) -> MultiAgentWorkflow:
        """Generate SQL queries based on user request."""

        parser = PydanticOutputParser(pydantic_object=SQLWriterOutput)

        agent_prompt = self.prompts.sql_writer_prompt.format(**{
            "fmt": parser.get_format_instructions(),
            "db": self.database_manager.database_model,
        })
        node_prompt = ChatPromptTemplate.from_messages([
            ("system", "{agent_propmpt}"),
            ("human", "{request}")
        ])
        response: SQLWriterOutput = await with_fallback(
            node_prompt | self.llm | parser,
            node_prompt | self.fallback_llm | parser,
            {"agent_propmpt": agent_prompt, "request": state["request"]}
        )
        update = {
            "sql": response.sql,
            "sql_explanation": response.sql_explanation,
            "interactions_history": state.get("interactions_history", []) + ["sql_writer"],
            "reasoning_traces": [{"reasoning": response.reasoning, "failure_reason": response.failure_reason}]
        }
        return update

    async def insight_generator_node(self, state: MultiAgentWorkflow) -> MultiAgentWorkflow:
        """Generate insights from data analysis or user-provided data."""

        parser = PydanticOutputParser(pydantic_object=InsightGeneratorOutput)

        agent_prompt = self.prompts.insight_generator_prompt.format(**{
            "fmt": parser.get_format_instructions(),
            "db": self.database_manager.database_model,
        })
        node_prompt = ChatPromptTemplate.from_messages([
            ("system", "{agent_propmpt}"),
            ("human", "{request}")
        ])

        if path := state.get("user_data_file"):

            user_provided_data = self.tools["read_provided_data"].invoke({"path": path})
            node_prompt.append(("ai", f"User provided data: {user_provided_data}"))

        response: InsightGeneratorOutput = await with_fallback(
            node_prompt | self.llm | parser,
            node_prompt | self.fallback_llm | parser,
            {"agent_propmpt": agent_prompt, "request": state["request"]
        })

        if response.sql and not path:
            queried_data = await self.tools["search_postgres_database"].ainvoke({"statement": response.sql})

            node_prompt.append(("ai", f"Extracted data: {queried_data}"))

            response: InsightGeneratorOutput = await with_fallback(
                node_prompt | self.llm | parser,
                node_prompt | self.fallback_llm | parser,
                {"agent_propmpt": agent_prompt, "request": state["request"]
            })

        update = {
            "queried_data": queried_data,
            "insights": response.insights,
            "interactions_history": state.get("interactions_history", []) + ["insight_generator"],
            "reasoning_traces": [{"reasoning": response.reasoning, "failure_reason": response.failure_reason}]
        }
        return update

    async def answer_summarizer_node(self, state: MultiAgentWorkflow) -> MultiAgentWorkflow:
        """Summarize results from all agents into final answer."""

        parser = PydanticOutputParser(pydantic_object=AnswerSummarizerOutput)

        node_prompt = ChatPromptTemplate.from_messages([
            ("system", "{agent_propmpt}"),
            ("human", "{request}")
        ])
        agent_prompt = self.prompts.answer_summarizer_prompt.format(**{
            "fmt": parser.get_format_instructions(),
            "sql": state.get("sql"),
            "sql_explanation": state.get("sql_explanation"),
            "insights": state.get("insights"),
            "queried_data": state.get("queried_data"),
        })
        response: AnswerSummarizerOutput = await with_fallback(
            node_prompt | self.llm | parser,
            node_prompt | self.fallback_llm | parser,
            {"agent_propmpt": agent_prompt, "request": state["request"]
        })
        update = {
            "answer": response,
            "interactions_history": state.get("interactions_history", []) + ["answer_summarizer"],
            "reasoning_traces": [{"reasoning": response.reasoning, "failure_reason": response.failure_reason}]
        }
        return update


async def provide_agentic_session(agent: CoffeeShopAnalystAsistant, stopword: str = "/stop_conversation") -> SessionTracing:
    """Run interactive session with the coffee shop analyst agent.

    Args:
        agent: Initialized analyst assistant instance.
        stopword: Command to end the conversation session.
    """

    greeting = "[Agent] I'm an analyst assistant, and I'm happy to answer your questions!" + "\n"
    farewell = "[Agent] All the best!"

    agentic_app = agent.compiled_graph

    session_history = []

    while (request := input(greeting)) != stopword:

        state: MultiAgentWorkflow = await agentic_app.ainvoke({"request": request})

        session_history.append({
           "answer": state["answer"].answer,
           "request": state["request"],
           "interactions_history": state["interactions_history"],
           "reasoning_traces": state["reasoning_traces"]
        })

        print(state["answer"].answer)
    else:
        print(farewell)

    session_trace = SessionTracing(session_id=uuid.uuid4(), session_history=session_history)
    await agent.database_manager.dump_object(session_trace)

    print("Session trace dumped successfully!")
    return session_trace
