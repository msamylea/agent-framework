# agents/base.py
from typing import List, Dict, Optional, Any, Union
from pydantic import BaseModel, Field
from tools.toolbox import tool_registry
from .models import ConversationTurn, AgentCapability
from schemas.resp_formats import TaskAnalysis, FinalResponse, CodeResponse
from prompt_templates.response_prompts import assign_tool_prompt, summarize_final_response, generate_code, handle_code_error
from utilities.errors import LLMConnectionError, LLMValidationError, LLMResponseError, ToolNotFoundError, ToolValidationError, ToolExecutionError
from datetime import datetime

class Agent(BaseModel):
    """Unified agent that handles task execution"""
    name: str
    description: str
    capabilities: List[AgentCapability]
    tools: Optional[List[Dict]] = None
    max_history: int = Field(default=50)
    history: List[ConversationTurn] = Field(default_factory=list)
    llm: Any = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tools = self.tools or []

    def add_tools(self, tools: List[Dict]):
        """Add tools to the agent"""
        self.tools = tools
        return self


    async def execute_task_and_format(self, task: Dict[str, Any], user_input: str) -> Dict[str, Any]:
        """Execute a task and format its response"""
        try:
            print(f"\nExecuting task: {task.get('name')}")
            
            # If this is a code task that needs code generation
            if task.get('tool') == 'execute_python_code':
                print("\nGenerating code based on task description and research...")
                
                # Get previous results if this task depends on others
                previous_results = task.get('parameters', {}).get('previous_results', '')
                
                # Generate code using LLM
                code_prompt = generate_code.replace(
                    "{{previous_results}}", str(previous_results)
                ).replace(
                    "{{task_description}}", task.get('description', '')
                )
                
                try:
                    code_response = await self.llm.chat(
                        role="user",
                        content=code_prompt,
                        response_model=CodeResponse
                    )
                    
                    # Add generated code to task parameters
                    task['parameters'] = {
                        'code': code_response.code,
                        'timeout': task.get('parameters', {}).get('timeout', 30)
                    }
                    
                    print("\nGenerated Code:")
                    print(code_response.code)
                    
                except Exception as e:
                    print(f"Error generating code: {str(e)}")
                    raise
            
            # Execute the task with potentially modified parameters
            result = await self.execute_task(task)
            
            # Format and show response
            print("\nFormatting response...")
            response = await self._format_response(result, user_input, task)
            
            # Update history
            self._update_history(user_input, response)
            
            return {
                'result': response,
                'status': result.get('status', 'unknown'),
                'formatted_output': response,
                'task_output': result
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"\nError executing task: {error_msg}")
            return {
                'error': error_msg,
                'status': 'error',
                'formatted_output': f"Error executing task: {error_msg}"
            }
        
    def _update_history(self, user_input: str, response: str) -> None:
        """Update conversation history"""
        turn = ConversationTurn(
            user_input=user_input,
            agent_response=response,
            timestamp=datetime.now()
        )
        self.history.append(turn)
        
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

    def clear_history(self) -> None:
        """Clear conversation history"""
        self.history = []

    def can_handle_task(self, task: Dict[str, Any]) -> bool:
        """Determine if agent can handle a task"""
        if not self.tools:
            return False
            
        # Get required function types for this task
        task_capabilities = task.get("required_capabilities", [])
        required_types = set()
        for cap in self.capabilities:
            if cap.name in task_capabilities:
                required_types.update(cap.function_types)
        
        # Get available function types from our tools
        available_types = {
            config.get("function_type") 
            for tool in self.tools 
            if (config := tool_registry.get_tool_config(tool["name"]))
        }
        
        return all(req_type in available_types for req_type in required_types)

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task using the tool chosen by LLM"""
        results = []
        try:
            tool_name = task["tool"]
            
            # Clean up parameters based on tool type
            tool_config = tool_registry.get_tool_config(tool_name)
            valid_params = tool_config.get("parameters", {}).keys()
            cleaned_parameters = {
                k: v for k, v in task.get("parameters", {}).items() 
                if k in valid_params
            }
            
            print("TOOL NAME: ", tool_name)
            print("CLEANED PARAMETERS: ", cleaned_parameters)
            
            try:
                print(f"\nExecuting {tool_name}...")
                if "code" in cleaned_parameters:
                    print("\nExecuting code...")
                    print("Code to execute:")
                    print(cleaned_parameters["code"])
                
                # Execute tool
                result = await tool_registry.execute_tool(tool_name, cleaned_parameters)
                if "code" in cleaned_parameters and "Error" in str(result):
                    print("CALLING REPAIR ERROR")
                    prompt = handle_code_error.replace(
                        "{{error_message}}", str(result)
                    ).replace(
                        "{{code}}", cleaned_parameters["code"]
                    ).replace(
                        "{{task_description}}", task.get("description", "")
                    )
                    
                    repair_response = await self.llm.chat(
                        role="user",
                        content=prompt,
                        response_model=CodeResponse
                    )

                    repaired_code = repair_response.code
                    print("REPAIRED CODE: ", repaired_code)
                
                    # Execute the repaired code
                    cleaned_parameters["code"] = repaired_code
                    result = await tool_registry.execute_tool(tool_name, cleaned_parameters)

                print("\nTool Output:")
                print(result)
                
                results.append({
                    "tool": tool_name,
                    "result": result,
                    "success": True,
                    "explanation": task.get("description", "")
                })
            
            except ToolExecutionError as e:
                results.append({
                    "tool": tool_name,
                    "error": str(e),
                    "success": False
                })

        except ToolNotFoundError as e:
            results.append({
                "tool": tool_name,
                "error": str(e),
                "success": False
            })
            
        # Add the return statement here
        return {
            "status": "success" if any(r["success"] for r in results) else "error",
            "results": results
        }
    
    async def _analyze_task(self, task_input: str) -> Dict[str, Any]:
        """Use LLM to analyze task and determine required tools and parameters"""
        try:
            # Get available tools and their capabilities
            available_tools = tool_registry.list_tools()
            tools_info = []
            for name, config in available_tools.items():
                tools_info.append(f"""
                    Tool: {name}
                    Description: {config['description']}
                    Type: {config['function_type']}
                    Parameters: {', '.join(config['parameters'].keys())}
                    """)

            # Create prompt for LLM
            prompt = assign_tool_prompt.replace("{{tools_info}}", "\n".join(tools_info)).replace("{{task_input}}", task_input)

            try:
                # Get LLM's analysis
                response = await self.llm.chat(
                    role="user",
                    content=prompt,
                    response_model=TaskAnalysis
                )

                # Map to task format
                return {
                    "id": str(hash(task_input)),
                    "name": response.tool_name,
                    "parameters": response.parameters
                }

            except LLMConnectionError as e:
                raise LLMConnectionError(f"LLM connection error during task analysis: {e.message}", e.base_url)
            except LLMValidationError as e:
                raise LLMValidationError(f"LLM validation error during task analysis: {e.message}", e.validation_errors)
            except LLMResponseError as e:
                raise LLMResponseError(f"LLM response error during task analysis: {e.message}", e.model, e.response_model)

        except Exception as e:
            raise e

    async def _format_response(self, result: Dict[str, Any], user_input: str, task) -> str:
        """Format task results into natural language response with error handling"""
        try:
            # Collect all results
            output_sections = []
            output_sections.append("=== Task Analysis ===")
            output_sections.append(f"Input: {user_input}")
            output_sections.append("")

            
            output_sections.append("After analysis, I have identified the following tasks to complete:")
            output_sections.append(f"Task: {task.get('name', 'Unknown task')}")
            output_sections.append(f"Tool: {task.get('name')}")
            if task.get('parameters'):
                output_sections.append("Parameters:")
                for param, value in task['parameters'].items():
                    output_sections.append(f"  {param}: {value}")
            output_sections.append("")

            for r in result.get("results", []):
                output_sections.append(f"=== Executing Tool: {r.get('tool', 'unknown')} ===")
                
                # Show explanation if available
                if r.get("explanation"):
                    output_sections.append(f"Purpose: {r['explanation']}")
                
                # Show the actual tool results or errors
                if r.get("success", False):
                    # Format code blocks properly
                    if isinstance(r["result"], str) and "```" in r["result"]:
                        output_sections.append("Generated Code:")
                        output_sections.append(r["result"])
                    else:
                        output_sections.append("Result:")
                        output_sections.append(str(r["result"]))
                else:
                    output_sections.append(f"Error: {r.get('error', 'Unknown error occurred')}")
                
                output_sections.append("")  # Add spacing between sections
                output_sections.append("=" * 30)
            # If no successful results were found
            if not any(r.get("success", False) for r in result.get("results", [])):
                output_sections.append("No successful results were obtained with the available tools.")
                output_sections.append("=" * 30)

            # Turn result dict into result str
            result = "\n".join(output_sections)
           
            prompt = summarize_final_response.replace("{{user_input}}", user_input).replace("{{tool_results}}", result)

            try:
                response = await self.llm.chat(
                    role="user",
                    content=prompt,
                    response_model=FinalResponse
                )
                return response.content

            except Exception as e:
                output_sections.append("=== Summary ===")
                output_sections.append("An error occurred while formatting the final response.")
                output_sections.append(f"Raw results are shown above.")
                output_sections.append("=" * 30)

            return "\n".join(output_sections)

        except Exception as e:
            return f"Error formatting response: {str(e)}\nRaw result: {str(result)}"