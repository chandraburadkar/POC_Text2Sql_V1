# app/main.py
from __future__ import annotations

import sys
from dotenv import load_dotenv

from app.graph.text2sql_graph import run_text2sql


def main():
    load_dotenv(override=True)

    if len(sys.argv) < 2:
        print('Usage: python -m app.main "your question here"')
        sys.exit(1)

    question = sys.argv[1]
    out = run_text2sql(question)

    if not out.get("ok"):
        print("FAILED:", out)
        sys.exit(2)

    print("\nUSER QUESTION:", question)
    print("\nREWRITTEN:", out.get("rewritten_query"))
    print("\nFINAL SQL:\n", out.get("final_sql"))

    df = out.get("result_df")
    if df is not None:
        print("\nRESULT PREVIEW:")
        print(out.get("dataframe", {}).get("preview_markdown", ""))

    print("\nEXPLANATION:\n", out.get("explanation", {}).get("summary", ""))


if __name__ == "__main__":
    main()