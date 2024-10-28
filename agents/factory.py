# agents/factory.py
from typing import List, Dict, Any
from .base import Agent
from .models import AgentCapability

def create_agent(name: str, description: str, capabilities: List[Dict[str, Any]], llm: Any = None) -> Agent:
    """Create new agent"""
    agent_capabilities = [
        AgentCapability(**capability) 
        for capability in capabilities
    ]
    
    return Agent(
        name=name,
        description=description,
        capabilities=agent_capabilities,
        llm=llm
    )