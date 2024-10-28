# schemas/resp_formats.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from instructor import Mode

class TaskAnalysis(BaseModel):
    """LLM's analysis of a user task"""
    tool_name: str = Field(..., description="Name of the tool to use")
    parameters: Dict[str, Any] = Field(default_factory=dict)

class TaskItem(BaseModel):
    """Single task item"""
    name: str = Field(..., description="Name of the task")
    description: str = Field(..., description="Description of what needs to be done")
    tool: str = Field(..., description="Name of the tool to use")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    class Config:
        mode = Mode.JSON

class TaskList(BaseModel):
    """List of tasks to be performed"""
    tasks: List[TaskItem] = Field(..., description="List of tasks to perform")

    class Config:
        mode = Mode.JSON

class ToolAssignment(BaseModel):
    """Tool assignment for a task"""
    task_name: str = Field(..., description="Name of the task this tool is for")
    tool_name: str = Field(..., description="Name of the tool to use")
    parameters: Dict[str, Any] = Field(..., description="Parameters for the tool")

    class Config:
        mode = Mode.JSON

class WebSearchResponse(BaseModel):
    """Input to a web search tool"""
    url: str = Field(..., description="URL to search")
    topic: str = Field(..., description="Topic to search for")

    class Config:
        mode = Mode.JSON
        
class FinalResponse(BaseModel):
    """Final response to user"""
    content: str = Field(..., description="The formatted response to return to the user")

class CodeResponse(BaseModel):
    """Response model for code generation"""
    code: str = Field(..., description="The generated Python code")

    class Config:
        mode = Mode.JSON