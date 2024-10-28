# tools/models.py
from typing import Dict, Any, Optional, Set
from pydantic import BaseModel, Field

class ToolState(BaseModel):
    """State container for tool registry"""
    tools: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    function_types: Dict[str, Set[str]] = Field(default_factory=dict)
    initialized_tools: Set[str] = Field(default_factory=set)
    allowed_modules: Set[str] = Field(default_factory=set)  


    def register_tool(self, name: str, config: Dict[str, Any]) -> None:
        """Register a tool with its configuration"""
        self.tools[name] = config
        
        # Register function type
        function_type = config.get("function_type")
        if function_type:
            if function_type not in self.function_types:
                self.function_types[function_type] = set()
            self.function_types[function_type].add(name)
        
        self.initialized_tools.add(name)

    def get_tools_by_type(self, function_type: str) -> Set[str]:
        """Get all tool names of a specific type"""
        return self.function_types.get(function_type, set())