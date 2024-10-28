# agents/models.py
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class ConversationTurn(BaseModel):
    user_input: str
    agent_response: str
    timestamp: datetime

class AgentCapability(BaseModel):
    """Defines what an agent can do"""
    name: str
    description: str
    function_types: List[str] = Field(description="Types of functions needed (e.g., ['search', 'web'])")
    parameters: Dict[str, Dict[str, Any]] = Field(default_factory=dict)