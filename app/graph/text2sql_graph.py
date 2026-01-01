from __future__ import annotations

from typing import Any, Dict, List

from app.audit.langsmith_tracing import tracing_session, traceable_fn
from app.state.agent_state import AgentState
from app.rag.schema_index import build_schema_index
from app.agents.query_rewriter import rewrite_query
from app.agents.sql_generator import generate_sql
from app.agents.sql_validator import validate_and_autofix_sql
from app.agents.sql_executor import execute_sql
from app.agents.explainer import explain_answer
from mcp.genie_mcp import GenieMCP
from mcp.cache_mcp import CacheMCP
from security.rbac import check_table_access

genie_mcp = GenieMCP(enabled=False)   # 🔒 Enable ONLY on DBX
cache_mcp = CacheMCP()


def _safe_get_sql(candidate_sql: Any) -> str:
    """
    candidate_sql can be:
    - dict from generate_sql() -> {"sql": "...", ...}
    - string (fallback)
    """
    if isinstance(candidate_sql, dict):
        return candidate_sql.get("sql", "") or ""
    if isinstance(candidate_sql, str):
        return candidate_sql
    return ""


@traceable_fn("run_text2sql")
def run_text2sql(
    user_question: str,
    persona: str = "analyst",  # ✅ NEW
    top_k_schema: int = 5,
    return_rows: int = 20,
    enable_viz: bool = False,
) -> Dict[str, Any]:

    with tracing_session():

        # -----------------------------
        # Init shared state
        # -----------------------------
        state = AgentState(user_question=user_question)
        state.persona = persona

        # -----------------------------
        # STEP 5: Query Rewriter
        # -----------------------------
        rew = rewrite_query(state.user_question)
        state.rewritten_query = rew.get("rewritten_query", state.user_question)
        state.intent = rew.get("intent", "UNKNOWN")
        state.entities = rew.get("entities", {}) or {}

        # -----------------------------
        # STEP 4: Schema RAG
        # -----------------------------
        vs = build_schema_index()
        docs = vs.similarity_search(state.rewritten_query, k=top_k_schema)

        state.schema_context = "\n\n".join(d.page_content for d in docs)

        tables: list[str] = []
        for d in docs:
            t = None
            if getattr(d, "metadata", None):
                t = d.metadata.get("table")
            if not t:
                first_line = (d.page_content or "").splitlines()[:1]
                if first_line and first_line[0].lower().startswith("table:"):
                    t = first_line[0].split(":", 1)[1].strip()
            if t:
                tables.append(t)

        state.retrieved_tables = list(dict.fromkeys(tables))

        # -----------------------------
        # 🔐 RBAC CHECK
        # -----------------------------
        if not check_table_access(state.persona, state.retrieved_tables):
            return {
                "ok": False,
                "stage": "rbac",
                "message": f"Persona '{persona}' not allowed to access tables",
                "retrieved_tables": state.retrieved_tables,
            }

        # -----------------------------
        # ⚡ CACHE CHECK
        # -----------------------------
        cached = cache_mcp.get(state.rewritten_query)
        if cached:
            return {**cached, "cached": True}

        # -----------------------------
        # 🧠 GENIE FAST PATH
        # -----------------------------
        if genie_mcp.enabled and genie_mcp.can_handle(state.intent):
            try:
                genie_out = genie_mcp.execute(state.rewritten_query)

                payload = {
                    "ok": True,
                    "intent": state.intent,
                    "entities": state.entities,
                    "rewritten_query": state.rewritten_query,
                    "retrieved_tables": state.retrieved_tables,
                    "final_sql": genie_out.get("sql"),
                    "result_df": genie_out.get("df"),
                    "explanation": "Generated via Genie",
                    "chart_path": None,
                }
                cache_mcp.set(state.rewritten_query, payload)
                return payload

            except Exception:
                pass  # 🔁 SAFE FALLBACK

        # -----------------------------
        # STEP 6: SQL Generator
        # -----------------------------
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
            }

        # -----------------------------
        # STEP 7: SQL Validator
        # -----------------------------
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
                "final_sql": state.final_sql,
            }

        # -----------------------------
        # STEP 8: SQL Execution
        # -----------------------------
        exec_out = execute_sql(state.final_sql, limit_preview=return_rows)
        state.dataframe = exec_out
        state.result_df = exec_out.get("df")

        # -----------------------------
        # STEP 9: Explanation
        # -----------------------------
        explanation = explain_answer(
            user_question=state.user_question,
            sql=state.final_sql,
            df=state.result_df,
        )
        state.explanation = explanation

        # -----------------------------
        # STEP 10: Final Response + Cache
        # -----------------------------
        response = {
            "ok": True,
            "intent": state.intent,
            "entities": state.entities,
            "rewritten_query": state.rewritten_query,
            "retrieved_tables": state.retrieved_tables,
            "candidate_sql": state.candidate_sql,
            "final_sql": state.final_sql,
            "fixed_by_llm": state.fixed_by_llm,
            "dataframe": state.dataframe,
            "result_df": state.result_df,
            "preview_markdown": exec_out.get("preview_markdown"),
            "explanation": state.explanation,
            "chart_path": None,
        }

        cache_mcp.set(state.rewritten_query, response)
        return response