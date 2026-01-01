from __future__ import annotations

from typing import Any, Dict, Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.graph.text2sql_graph import run_text2sql
from app.api.schemas import Text2SQLRequest, Text2SQLResponse


router = APIRouter()

@router.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok"}


@router.post("/text2sql", response_model=Text2SQLResponse)
def text2sql(req: Text2SQLRequest):
    try:
        result = run_text2sql(
            user_question=req.question,
            persona=req.persona,
            top_k_schema=req.top_k_schema,
            return_rows=req.return_rows,
            enable_viz=req.enable_viz,
        )
        return result
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))