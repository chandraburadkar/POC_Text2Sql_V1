# app/agents/query_rewriter.py
from app.audit.langsmith_tracing import traceable_fn

import logging
from datetime import datetime
from typing import Dict, Any

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from app.agents.llm_factory import get_llm

logger = logging.getLogger(__name__)


# -----------------------------
# Structured Output Schema
# -----------------------------
class QueryRewriteOutput(BaseModel):
    rewritten_query: str = Field(
        ..., description="Clear, SQL-friendly version of the user question"
    )
    intent: str = Field(
        ..., description="User intent: KPI | TREND | RANKING | ROOT_CAUSE | ANOMALY"
    )
    entities: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted entities like airport, date range, metric"
    )
    clarification_needed: bool = Field(
        ..., description="True if user question is ambiguous"
    )
    clarification_question: str = Field(
        ..., description="Follow-up question if clarification is needed"
    )
    notes: str = Field(
        ..., description="Internal reasoning notes (for audit/debug)"
    )


# -----------------------------
# Prompt Template
# -----------------------------
def _rewrite_prompt(parser: PydanticOutputParser) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
You are an airport operations analytics expert.

Your task:
1. Understand the user's question
2. Rewrite it into a precise analytics question
3. Identify intent and entities
4. Decide if clarification is needed

Respond STRICTLY in JSON using the provided schema.
                """.strip(),
            ),
            (
                "human",
                "User question:\n{query}\n\n{format_instructions}",
            ),
        ]
    )


# -----------------------------
# Public Function
# -----------------------------
@traceable_fn("query_rewriter")
def rewrite_query(user_query: str) -> Dict[str, Any]:
    """
    Runs the Query Rewriter Agent.
    Returns structured JSON for downstream agents.
    """

    llm = get_llm(temperature=0.0)

    parser = PydanticOutputParser(pydantic_object=QueryRewriteOutput)
    prompt = _rewrite_prompt(parser)

    try:
        chain = prompt | llm | parser

        result: QueryRewriteOutput = chain.invoke(
            {
                "query": user_query,
                "format_instructions": parser.get_format_instructions(),
            }
        )

        output = result.model_dump()
        output["timestamp_utc"] = datetime.utcnow().isoformat()
        return output

    except Exception as e:
        logger.error("Query rewrite failed", exc_info=True)

        return {
            "rewritten_query": user_query,
            "intent": "UNKNOWN",
            "entities": {},
            "clarification_needed": False,
            "clarification_question": "",
            "notes": f"Rewrite failed: {e}",
            "timestamp_utc": datetime.utcnow().isoformat(),
        }