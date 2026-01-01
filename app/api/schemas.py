from pydantic import BaseModel
from typing import Optional, Any, Dict


class Text2SQLRequest(BaseModel):
    question: str
    persona: str = "analyst"
    top_k_schema: int = 5
    return_rows: int = 20
    enable_viz: bool = False


class Text2SQLResponse(BaseModel):
    ok: bool
    final_sql: Optional[str] = None
    preview_markdown: Optional[str] = None
    explanation: Optional[Any] = None
    intent: Optional[str] = None
    entities: Optional[Dict[str, Any]] = None
    cached: Optional[bool] = False
