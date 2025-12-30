# app/state/agent_state.py
from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class AgentState(BaseModel):
    # Inputs
    user_question: str

    # Step 5: rewriter
    rewritten_query: Optional[str] = None
    intent: Optional[str] = None
    entities: Dict[str, Any] = Field(default_factory=dict)

    # Step 4: schema retrieval
    schema_context: Optional[str] = None
    retrieved_tables: Optional[list[str]] = None

    # Step 6/7: SQL
    candidate_sql: Optional[str] = None
    final_sql: Optional[str] = None
    validation_ok: bool = False
    validation_error: Optional[str] = None
    fixed_by_llm: bool = False

    # Step 8: execution + explanation
    result_df: Optional[Any] = None   # Pandas DF
    explanation: Optional[str] = None
    chart_path: Optional[str] = None

    # Debug/Audit
    debug: Dict[str, Any] = Field(default_factory=dict)