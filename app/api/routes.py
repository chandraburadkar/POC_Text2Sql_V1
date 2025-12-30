from __future__ import annotations

from typing import Any, Dict, Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.graph.text2sql_graph import run_text2sql

router = APIRouter()


class Text2SQLRequest(BaseModel):
    question: str = Field(..., description="User natural language question")
    top_k_schema: int = Field(5, ge=1, le=20)
    return_rows: int = Field(20, ge=1, le=500)
    enable_viz: bool = Field(False, description="Reserved for future chart generation")


class Text2SQLResponse(BaseModel):
    ok: bool
    final_sql: Optional[str] = None
    preview_markdown: Optional[str] = None
    explanation: Optional[Dict[str, Any]] = None
    intent: Optional[str] = None
    entities: Optional[Dict[str, Any]] = None
    retrieved_tables: Optional[List[str]] = None
    debug: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    stage: Optional[str] = None


@router.get("/")
def api_root() -> Dict[str, Any]:
    return {
        "message": "GARV API router is active",
        "endpoints": {
            "health": "/api/health",
            "text2sql": "/api/text2sql",
        },
    }


@router.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok"}


@router.post("/text2sql", response_model=Text2SQLResponse)
def text2sql(req: Text2SQLRequest) -> Dict[str, Any]:
    """
    Runs the full Text2SQL pipeline and returns:
    - final_sql
    - preview markdown
    - explanation
    """
    try:
        out = run_text2sql(
            user_question=req.question,
            top_k_schema=req.top_k_schema,
            return_rows=req.return_rows,
            enable_viz=req.enable_viz,
        )

        if out.get("ok"):
            return {
                "ok": True,
                "final_sql": out.get("final_sql"),
                "preview_markdown": out.get("preview_markdown"),
                "explanation": out.get("explanation"),
                "intent": out.get("intent"),
                "entities": out.get("entities"),
                "retrieved_tables": out.get("retrieved_tables"),
                "debug": out.get("debug"),
            }

        return {
            "ok": False,
            "stage": out.get("stage"),
            "message": out.get("message"),
            "intent": out.get("intent"),
            "entities": out.get("entities"),
            "retrieved_tables": out.get("retrieved_tables"),
            "debug": out.get("debug"),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))