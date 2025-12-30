# app/graph/text2sql_graph.py
from app.audit.langsmith_tracing import tracing_session, traceable_fn
from __future__ import annotations

from typing import Any, Dict, Optional, List

from app.state.agent_state import AgentState
from app.rag.schema_index import build_schema_index
from app.agents.query_rewriter import rewrite_query
from app.agents.sql_generator import generate_sql
from app.agents.sql_validator import validate_and_autofix_sql
from app.agents.sql_executor import execute_sql
from app.agents.explainer import explain_answer


def _safe_get_sql(candidate_sql: Any) -> str:
    """
    candidate_sql can be:
    - dict from generate_sql() -> {"sql": "...", ...}
    - string (if someone changes generator later)
    This helper makes the graph robust.
    """
    if isinstance(candidate_sql, dict):
        return candidate_sql.get("sql", "") or ""
    if isinstance(candidate_sql, str):
        return candidate_sql
    return ""

@traceable_fn("run_text2sql")
def run_text2sql(
    user_question: str,
    top_k_schema: int = 5,
    return_rows: int = 20,
    enable_viz: bool = False,  # kept for later steps
) -> Dict[str, Any]:
    """
    End-to-end Text2SQL pipeline.
    Returns a stable, notebook-friendly response contract.
    """
    with tracing_session():

        state = AgentState(user_question=user_question)

        # STEP 5: Query Rewriter
        rew = rewrite_query(state.user_question)
        state.rewritten_query = rew.get("rewritten_query", state.user_question)
        state.intent = rew.get("intent", "UNKNOWN")
        state.entities = rew.get("entities", {}) or {}

        # STEP 4: Schema RAG (retrieve schema context)
        vs = build_schema_index()
        docs = vs.similarity_search(state.rewritten_query, k=top_k_schema)
        state.schema_context = "\n\n".join([d.page_content for d in docs])

        # Best-effort: store retrieved table names if present in metadata/content
        tables: List[str] = []
        for d in docs:
            t = None
            if getattr(d, "metadata", None):
                t = d.metadata.get("table")
            if not t:
                # fallback parse from page_content line "Table: xyz"
                first_line = (d.page_content or "").splitlines()[0:1]
                if first_line and first_line[0].lower().startswith("table:"):
                    t = first_line[0].split(":", 1)[1].strip()
            if t:
                tables.append(t)
        state.retrieved_tables = list(dict.fromkeys(tables))

        # STEP 6: SQL Generator (returns dict)
        cand = generate_sql(
            rewritten_query=state.rewritten_query,
            schema_context=state.schema_context,
            intent=state.intent,
            entities=state.entities,
            user_question=state.user_question,
        )
        state.candidate_sql = cand

        candidate_sql_str = _safe_get_sql(cand)
        if not candidate_sql_str.strip():
            return {
                "ok": False,
                "stage": "sql_generation",
                "message": "SQL generator returned empty SQL.",
                "intent": state.intent,
                "entities": state.entities,
                "rewritten_query": state.rewritten_query,
                "retrieved_tables": state.retrieved_tables,
                "candidate_sql": cand,
                "debug": {"rewriter": rew},
            }

        # STEP 7: SQL Validator + Auto-fix (expects schema_context + candidate_sql string)
        val = validate_and_autofix_sql(
            rewritten_query=state.rewritten_query,
            schema_context=state.schema_context,
            candidate_sql=candidate_sql_str,
            max_retries=1,
        )

        state.validation_ok = bool(val.get("ok"))
        state.final_sql = val.get("final_sql", candidate_sql_str)
        state.fixed_by_llm = bool(val.get("fixed_by_llm"))

        if not state.validation_ok:
            return {
                "ok": False,
                "stage": "sql_validation",
                "message": "SQL validation failed.",
                "intent": state.intent,
                "entities": state.entities,
                "rewritten_query": state.rewritten_query,
                "retrieved_tables": state.retrieved_tables,
                "candidate_sql": cand,
                "final_sql": state.final_sql,
                "fixed_by_llm": state.fixed_by_llm,
                "debug": {"rewriter": rew, "validator": val},
            }

        # STEP 8: SQL Execution (your executor returns dict with df inside)
        exec_out = execute_sql(state.final_sql, limit_preview=return_rows)
        # state.dataframe = exec_out

        # STEP 8: Explanation (call explainer with signature it supports)
        # Your explainer currently doesn't accept intent/entities (you got that error),
        # so we only pass the common args.
        explanation = explain_answer(
            user_question=state.user_question,
            sql=state.final_sql,
            df=exec_out.get("df"),
        )
        state.explanation = explanation

        # STEP 10: Stable response contract (aliases added)
        return {
            "ok": True,
            "intent": state.intent,
            "entities": state.entities,
            "rewritten_query": state.rewritten_query,
            "retrieved_tables": state.retrieved_tables,
            "candidate_sql": cand,                 # dict from generator
            "final_sql": state.final_sql,          # string
            "fixed_by_llm": state.fixed_by_llm,

            # executor output
            "dataframe": exec_out,                 # dict (df, preview_markdown, row_count, columns)

            # notebook-friendly aliases
            "result_df": exec_out.get("df"),       # <-- THIS fixes your KeyError
            "preview_markdown": exec_out.get("preview_markdown", ""),
            "row_count": exec_out.get("row_count", 0),
            "columns": exec_out.get("columns", []),

            "explanation": explanation,
            "chart_path": None,  # reserved for Step 11
            "debug": {"rewriter": rew, "validator": val},
        }