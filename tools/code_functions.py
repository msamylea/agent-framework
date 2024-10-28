import ast
import io
import sys
import importlib
from typing import Optional
from .toolbox import tool, tool_registry

@tool('code')
async def execute_python_code(code: str, timeout: Optional[int] = 30) -> str:
    """Execute Python code and return result."""
    try:
        # Get tool configuration using correct name from decorator
        tool_config = tool_registry.get_tool_config('execute_python_code')
        if not tool_config:
            raise ValueError("Tool configuration not found")

        allowed_modules = set(tool_config.get('allowed_modules', []))
        blocked_modules = set(tool_config.get('blocked_modules', []))

        # Parse and validate imports
        tree = ast.parse(code)
        required_imports = set()
        
        # Analyze code for imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in blocked_modules:
                        raise ValueError(f"Importing {alias.name} is not allowed")
                    if alias.name in allowed_modules:
                        required_imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module in blocked_modules:
                    raise ValueError(f"Importing from {node.module} is not allowed")
                if node.module in allowed_modules:
                    required_imports.add(node.module)

        # Create execution environment with allowed imports
        globals_dict = {'__builtins__': __builtins__}
        for module_name in required_imports:
            try:
                module = importlib.import_module(module_name)
                globals_dict[module_name] = module
            except ImportError as e:
                raise ValueError(f"Could not import {module_name}: {str(e)}")

        # Execute with validated imports
        stdout = io.StringIO()
        sys.stdout = stdout
        
        try:
            exec(code, globals_dict, {})
            output = stdout.getvalue()
        finally:
            sys.stdout = sys.__stdout__
        
        return output if output else "Code executed successfully (no output)"
        
    except Exception as e:
        return f"Error executing code: {str(e)}"