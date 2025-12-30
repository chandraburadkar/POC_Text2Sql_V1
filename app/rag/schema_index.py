# app/rag/schema_index.py
from __future__ import annotations

import os
from typing import Optional, List

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from app.rag.embeddings_factory import get_embeddings
from app.rag.schema_docs import extract_schema_docs

DEFAULT_CHROMA_DIR = os.getenv("CHROMA_SCHEMA_DIR", "data/chroma_schema_index")

_vectorstore: Optional[Chroma] = None


def build_schema_index(persist_dir: str = DEFAULT_CHROMA_DIR) -> Chroma:
    """
    Build and persist schema index into Chroma.
    """
    os.makedirs(persist_dir, exist_ok=True)

    docs: List[Document] = extract_schema_docs()
    if not docs:
        raise RuntimeError("No schema docs found. Is DuckDB loaded with tables?")

    embeddings = get_embeddings()

    # Build from documents and persist
    vs = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=persist_dir,
    )
    vs.persist()
    return vs


def get_schema_vectorstore(persist_dir: str = DEFAULT_CHROMA_DIR) -> Chroma:
    """
    Load the persisted Chroma schema index.
    If missing/empty, rebuild.
    """
    global _vectorstore
    if _vectorstore is not None:
        return _vectorstore

    embeddings = get_embeddings()

    # Try load
    vs = Chroma(
        persist_directory=persist_dir,
        embedding_function=embeddings,
    )

    # If empty -> rebuild
    try:
        count = vs._collection.count()
    except Exception:
        count = 0

    if count == 0:
        vs = build_schema_index(persist_dir=persist_dir)

    _vectorstore = vs
    return _vectorstore

