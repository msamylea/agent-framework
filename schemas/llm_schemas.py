# schemas/llm_schemas.py
from typing import Optional
from pydantic import BaseModel, Field

class CapabilityParameters(BaseModel):
    """Base parameters that all capabilities can use"""
    search_query: Optional[str] = None
    max_results: Optional[int] = Field(default=5)
    code: Optional[str] = None
    timeout: Optional[int] = Field(default=30)
    url: Optional[str] = None