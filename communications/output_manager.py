# utilities/output_manager.py
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from utilities.errors import AppError


class OutputResult(BaseModel):
    """Model for individual task/action results"""
    task_id: str
    agent_name: Optional[str]
    timestamp: datetime = Field(default_factory=datetime.now)
    status: str
    result: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class OutputSummary(BaseModel):
    """Model for aggregated results"""
    request_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    results: List[OutputResult]
    overall_status: str
    execution_time: float

class OutputManagerModel(BaseModel):
    """Pydantic model for OutputManager state"""
    results: List[OutputResult] = Field(default_factory=list)
    start_time: Optional[datetime] = None
    request_id: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

class OutputManager:
    """Manages collection and processing of task results"""
    def __init__(self):
        self.state = OutputManagerModel()

    def start_request(self, request_id: str):
        """Start tracking a new request"""
        self.state.results = []
        self.state.start_time = datetime.now()
        self.state.request_id = request_id

    def add_result(self, 
                  task_id: str,
                  status: str,
                  result: Any,
                  agent_name: Optional[str] = None,
                  error: Optional[str] = None,
                  metadata: Optional[Dict[str, Any]] = None):
        """Add a task/action result"""
        try:
            output_result = OutputResult(
                task_id=task_id,
                agent_name=agent_name,
                status=status,
                result=result,
                error=error,
                metadata=metadata or {}
            )
            self.state.results.append(output_result)
        except Exception as e:
            raise AppError(f"Error adding result: {str(e)}")

    def get_summary(self) -> OutputSummary:
        """Generate summary of all results"""
        if not self.state.start_time or not self.state.request_id:
            raise AppError("No active request found")

        execution_time = (datetime.now() - self.state.start_time).total_seconds()
        successful = sum(1 for r in self.state.results if r.status == "success")
        failed = sum(1 for r in self.state.results if r.status == "error")

        return OutputSummary(
            request_id=self.state.request_id,
            total_tasks=len(self.state.results),
            successful_tasks=successful,
            failed_tasks=failed,
            results=self.state.results,
            overall_status="success" if failed == 0 else "partial" if successful > 0 else "error",
            execution_time=execution_time
        )

    def format_output(self, response: Dict[str, Any]) -> str:
        if isinstance(response, str):
            return response
            
        formatted = []
        formatted.append("=== Results ===")
        
        if 'result' in response:
            formatted.append(str(response['result']))
            
        if 'error' in response:
            formatted.append(f"Error: {response['error']}")
            
        if not formatted:
            formatted.append("No results available")
            
        return "\n".join(formatted)

    def clear(self):
        """Clear current results"""
        self.state = OutputManagerModel()
