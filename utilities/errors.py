# utilities/errors.py
from typing import Optional, Any, Dict, List

class AppError(Exception):
    """Base error class for application"""
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

class ConfigError(AppError):
    """Configuration related errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CONFIG_ERROR", details)

class ToolError(AppError):
    """Base class for tool-related errors"""
    def __init__(
        self,
        message: str,
        tool_name: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message,
            "TOOL_ERROR",
            {
                "tool_name": tool_name,
                **(details or {})
            }
        )

class ToolNotFoundError(ToolError):
    """Error when a requested tool doesn't exist"""
    def __init__(self, tool_name: str):
        super().__init__(
            f"Tool not found: {tool_name}",
            tool_name
        )

class ToolConfigError(ToolError):
    """Error in tool configuration"""
    def __init__(
        self,
        tool_name: str,
        config_issues: List[str],
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Invalid tool configuration: {tool_name}",
            tool_name,
            {
                "config_issues": config_issues,
                **(details or {})
            }
        )

class ToolExecutionError(ToolError):
    """Error during tool execution"""
    def __init__(
        self,
        tool_name: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message,
            tool_name,
            details
        )

class ToolValidationError(ToolError):
    """Error in tool parameter validation"""
    def __init__(
        self,
        tool_name: str,
        invalid_params: Dict[str, str],
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Invalid parameters for tool: {tool_name}",
            tool_name,
            {
                "invalid_params": invalid_params,
                **(details or {})
            }
        )

class LLMError(AppError):
    """Base class for LLM-related errors"""
    def __init__(
        self, 
        message: str, 
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "LLM_ERROR", details)

class LLMConnectionError(LLMError):
    """Error when connecting to LLM service"""
    def __init__(
        self, 
        message: str, 
        base_url: str, 
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message,
            {
                "base_url": base_url,
                **(details or {})
            }
        )

class LLMResponseError(LLMError):
    """Error when processing LLM response"""
    def __init__(
        self, 
        message: str, 
        model: str, 
        response_model: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message,
            {
                "model": model,
                "response_model": response_model,
                **(details or {})
            }
        )

class LLMValidationError(LLMError):
    """Error when validating LLM inputs or outputs"""
    def __init__(
        self, 
        message: str, 
        validation_errors: list,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message,
            {
                "validation_errors": validation_errors,
                **(details or {})
            }
        )