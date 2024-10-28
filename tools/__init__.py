# tools/__init__.py

# First, import the registry and decorator
from .toolbox import tool_registry, tool

# Then import all function modules
from .code_functions import *
from .search_functions import *
from .web_functions import *

# Export what we want available
__all__ = [
    'tool_registry',
    'tool',
    # Code functions
    'execute_python_code',
    # Search functions
    'ddg_search',
    # Web functions
    'get_web_page'
]