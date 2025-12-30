# app/pipelines/03_build_schema_index.py
from __future__ import annotations

from app.rag.schema_index import build_schema_index


def main():
    vs = build_schema_index()
    print("✅ Schema index built successfully.")
    print("Collection size:", vs._collection.count())


if __name__ == "__main__":
    main()