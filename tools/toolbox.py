# tools/toolbox.py
from typing import Any, Dict, Callable, Optional
from functools import wraps
import yaml
from pydantic import BaseModel, Field, ValidationError
import asyncio
import threading
import inspect
from pathlib import Path
from tools.models import ToolState
from utilities.errors import ToolError, ToolConfigError, ToolNotFoundError, ToolValidationError, ToolExecutionError


class ToolConfig(BaseModel):
    """Tool configuration and metadata"""
    function: str
    description: str
    function_type: str  
    parameters: Dict[str, Dict[str, Any]]
    returns: str
    requires: Optional[list[str]] = Field(default_factory=list)
    validation: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ToolRegistry:
    """Registry for tool functions with enhanced error handling"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, config_path: Optional[str] = None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ToolRegistry, cls).__new__(cls)
                # Initialize instance attributes here
                cls._instance.config_path = config_path or Path(__file__).parent / "config" / "tools.yaml"
                cls._instance.state = ToolState()
                cls._instance.functions = {}
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, config_path: Optional[str] = None):
        # Initialize even if config is not present
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._initialized = True  # Set this first to prevent recursion
                    if config_path:
                        self.config_path = Path(config_path)

    def register_function(self, func: Callable, function_type: str) -> Callable:
        """Register a function as a tool with parameter inference"""
        with self._lock:
            try:
                name = func.__name__
                self.functions[name] = func
                
                # Get function signature for parameter info
                sig = inspect.signature(func)
                parameters = {}
                
                for param_name, param in sig.parameters.items():
                    if param_name == 'self':  # Skip self for methods
                        continue
                        
                    param_info = {
                        "type": "string",  # Default to string
                        "description": "",
                        "required": param.default == inspect.Parameter.empty
                    }
                    
                    # Try to infer type from annotation
                    if param.annotation != inspect.Parameter.empty:
                        if param.annotation == int:
                            param_info["type"] = "integer"
                        elif param.annotation == float:
                            param_info["type"] = "float"
                        elif param.annotation == bool:
                            param_info["type"] = "boolean"
                        elif param.annotation == str:
                            param_info["type"] = "string"
                    
                    # Add default if present
                    if param.default != inspect.Parameter.empty and param.default is not None:
                        param_info["default"] = param.default
                    
                    parameters[param_name] = param_info

                # Create tool config
                config = {
                    "function": f"{func.__module__}.{name}",
                    "function_type": function_type,
                    "description": func.__doc__ or "",
                    "parameters": parameters,
                    "returns": "string"
                }
                
                # Register in state
                self.state.register_tool(name, config)
                return func
                
            except Exception as e:
                raise ToolConfigError(
                    func.__name__,
                    ["Failed to register function"],
                    {"error": str(e)}
                )

    def load_tools(self) -> None:
        """Load tool configurations with validation"""
        try:
            # Check if config file exists
            if not self.config_path.exists():
                return 

            with open(self.config_path) as f:
                config = yaml.safe_load(f)

            if not isinstance(config, dict) or "tools" not in config:
                return

            for tool_name, tool_config in config["tools"].items():
                try:
                    # Skip already initialized tools
                    if tool_name in self.state.initialized_tools:
                        continue

                    # Validate tool configuration
                    self._validate_tool_config(tool_name, tool_config)
                    
                    # Register validated tool
                    self.state.register_tool(tool_name, tool_config)
                    
                except Exception as e:
                    continue  # Skip this tool but continue loading others

        except Exception as e:
            raise ToolConfigError(
                "ToolRegistry",
                ["Error loading tools"],
                {"error": str(e)}
            )

    def get_tool_config(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get tool configuration"""
        # Lazy load tools if not already loaded
        if not self.state.tools:
            self.load_tools()
        return self.state.tools.get(tool_name)

    def list_tools(self) -> Dict[str, Dict[str, Any]]:
        """Get all tool configurations"""
        # Lazy load tools if not already loaded
        if not self.state.tools:
            self.load_tools()
        return self.state.tools.copy()

    def _validate_tool_config(self, tool_name: str, config: Dict[str, Any]) -> None:
        """Validate tool configuration"""
        required_fields = ["function", "description", "function_type", "parameters"]
        missing_fields = [field for field in required_fields if field not in config]
        
        if missing_fields:
            raise ToolConfigError(
                tool_name,
                ["Missing required configuration fields"],
                {"missing_fields": missing_fields}
            )

        # Validate parameters schema
        for param_name, param_config in config["parameters"].items():
            if "type" not in param_config:
                raise ToolConfigError(
                    tool_name,
                    [f"Missing type for parameter: {param_name}"],
                    {"parameter": param_name}
                )

    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Execute a tool with comprehensive error handling"""
        if tool_name not in self.state.tools:
            raise ToolNotFoundError(tool_name)
            
        tool_config = self.state.tools[tool_name]
        
        try:
            # Validate parameters
            validated_params = self._validate_parameters(tool_name, parameters)
            
            try:
                if "code" in validated_params:
                    validated_params["code"] = validated_params["code"].strip()
                else:
                    validated_params = validated_params
            except Exception as e:
                raise ToolValidationError(
                    tool_name,
                    {"code": "Code parameter is required"},
                    {"raw_parameters": parameters}
                )

            # Get the tool function
            func = self.functions.get(tool_name)
            if not func:
                raise ToolNotFoundError(tool_name)

            # Apply any tool-specific validation
            validation_config = tool_config.get("validation", {})
            self._apply_validation(tool_name, validation_config, validated_params)
            
            # Execute with timeout
            timeout = parameters.get("timeout", 30)  # Default 30 seconds
            try:
                result = await asyncio.wait_for(
                    func(**validated_params),
                    timeout=timeout
                )
                print(f"Called {func.__name__} with parameters: {validated_params}")
                return result
                
            except asyncio.TimeoutError:
                raise ToolExecutionError(
                    tool_name,
                    "Tool execution timed out",
                    {
                        "timeout": timeout,
                        "parameters": validated_params
                    }
                )
                
        except ValidationError as e:
            raise ToolValidationError(
                tool_name,
                {err["loc"][0]: err["msg"] for err in e.errors()},
                {"raw_parameters": parameters}
            )
            
        except Exception as e:
            if isinstance(e, ToolError):
                raise
            raise ToolExecutionError(
                tool_name,
                "Tool execution failed",
                {
                    "error": str(e),
                    "parameters": parameters
                }
            )

    def _validate_parameters(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate tool parameters with detailed error reporting"""
        tool_config = self.state.tools[tool_name]
        param_specs = tool_config["parameters"]
        validated = {}
        invalid_params = {}
        
        # Check for unknown parameters
        unknown_params = set(parameters) - set(param_specs)
        if unknown_params:
            raise ToolValidationError(
                tool_name,
                {param: "Unknown parameter" for param in unknown_params}
            )
        
        # Validate each parameter
        for param_name, spec in param_specs.items():
            value = parameters.get(param_name)
            
            # Check required parameters
            if spec.get("required", False) and value is None:
                invalid_params[param_name] = "Required parameter missing"
                continue
                
            # Apply default if needed
            if value is None and "default" in spec:
                value = spec["default"]
            
            # Type validation
            if value is not None:
                try:
                    param_type = spec["type"]
                    if param_type == "int":
                        value = int(value)
                    elif param_type == "float":
                        value = float(value)
                    elif param_type == "bool":
                        value = bool(value)
                    elif param_type == "string":
                        value = str(value)
                    # Add more type validations as needed
                except (ValueError, TypeError):
                    invalid_params[param_name] = f"Invalid type. Expected {spec['type']}"
                    continue
                
            validated[param_name] = value
        
        if invalid_params:
            raise ToolValidationError(tool_name, invalid_params)
            
        return validated

    def _apply_validation(self, tool_name: str, validation: Dict[str, Any], parameters: Dict[str, Any]) -> None:
        """Apply tool-specific validation rules"""
        try:
            if "code" in parameters and "blocked_modules" in validation:
                code = parameters["code"]
                for module in validation["blocked_modules"]:
                    if f"import {module}" in code or f"from {module}" in code:
                        raise ToolValidationError(
                            tool_name,
                            {"code": f"Use of module '{module}' is not allowed"},
                            {"blocked_module": module}
                        )
                        
            # Add more validation rules as needed
            
        except Exception as e:
            if isinstance(e, ToolError):
                raise
            raise ToolValidationError(
                tool_name,
                {"validation": str(e)}
            )

tool_registry = ToolRegistry()

def tool(function_type: str):
    """Enhanced decorator for registering tools"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tool_name = func.__name__
            try:
                result = await func(*args, **kwargs)
                return result
                
            except Exception as e:
                if isinstance(e, ToolError):
                    raise
                raise ToolExecutionError(
                    tool_name,
                    "Tool execution failed",
                    {
                        "error": str(e),
                        "args": args,
                        "kwargs": kwargs
                    }
                )
                
        # Register with validation
        try:
            return tool_registry.register_function(wrapper, function_type)
        except Exception as e:
            raise ToolConfigError(
                func.__name__,
                ["Failed to register tool"],
                {"error": str(e)}
            )
            
    return decorator