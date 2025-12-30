# app/rag/schema_docs.py
from __future__ import annotations

from typing import List
from langchain_core.documents import Document

from app.db.duckdb_client import get_conn


def extract_schema_docs() -> List[Document]:
    """
    Builds LangChain Documents for each DuckDB table schema.
    Each Document has:
      - page_content: human-readable schema text
      - metadata: {"table": "<table_name>"}
    """

    conn = get_conn()

    tables = conn.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'main'
        ORDER BY table_name
    """).fetchall()

    docs: List[Document] = []

    for (table,) in tables:
        cols = conn.execute(f"""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'main'
              AND table_name = '{table}'
            ORDER BY ordinal_position
        """).fetchall()

        schema_text = "Table: " + table + "\nColumns:\n" + "\n".join(
            [f"- {c} ({t})" for c, t in cols]
        )

        docs.append(
            Document(
                page_content=schema_text,
                metadata={"table": table}  # ✅ now metadata works
            )
        )

    return docs