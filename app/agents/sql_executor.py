# app/agents/sql_executor.py

from __future__ import annotations


from app.audit.langsmith_tracing import traceable_fn
from typing import Any, Dict, Optional
import pandas as pd
import re

from app.db.duckdb_client import get_conn


_LIMIT_REGEX = re.compile(r"\blimit\b", re.IGNORECASE)

@traceable_fn("sql_executor")
def execute_sql(
    final_sql: str,
    limit: Optional[int] = None,        # <-- added
    limit_preview: int = 20,
) -> Dict[str, Any]:
    """
    Executes SQL in DuckDB and returns:
      - full dataframe (df)
      - preview markdown
      - row_count
      - columns

    `limit`:
      Optional hard cap on rows (used by graph / UI safety).
      Applied ONLY if SQL does not already contain LIMIT.
    """

    conn = get_conn()

    sql_to_run = final_sql.strip().rstrip(";")

    # Apply limit only if not already present
    if limit and limit > 0 and not _LIMIT_REGEX.search(sql_to_run):
        sql_to_run = f"{sql_to_run} LIMIT {int(limit)}"

    df: pd.DataFrame = conn.execute(sql_to_run).df()

    out = {
        "row_count": int(df.shape[0]),
        "columns": list(df.columns),
        "df": df,  # full dataframe for downstream agents
        "preview_markdown": (
            df.head(limit_preview).to_markdown(index=False)
            if not df.empty
            else ""
        ),
    }
    return out