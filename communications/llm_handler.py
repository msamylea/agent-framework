from prompt_templates.response_prompts import (
    decompose_tasks_prompt,
    assign_tool_prompt,
    generate_final_response
)
from tools.toolbox import invoke_tools, ToolInvocation, tool_registry
# Import all tools to ensure they're registered
from schemas.resp_formats import TaskList, ToolAssignment, FinalResponse
from configurations.llm_client import LLMClient
from pydantic import BaseModel
from typing import Any


llm_client = LLMClient()

def get_available_tools():
    """Get list of available tools and their metadata."""
    tools = tool_registry.get_tools()
    
    # Get metadata but format it in a more LLM-friendly way
    metadata = tool_registry.get_metadata()
    formatted_metadata = []
    
    for name, info in metadata.items():
        tool_desc = f"""Tool: {name}
Description: {info['description']}
Parameters: {', '.join(info['parameters'].keys())}
"""
        formatted_metadata.append(tool_desc)
    
    formatted_tools = "\n\n".join(formatted_metadata)
    
    return formatted_tools

def call_llm_with_retry(role: str, content: str, response_model: type[BaseModel], max_retries: int = 3) -> Any:
    """Call LLM with retry logic, using instructor for response parsing."""
    for attempt in range(max_retries):
        try:
            response = llm_client.chat(role=role, content=content, response_model=response_model)
            return response
        except Exception as e:
            if attempt == max_retries - 1:
                raise e

def determine_action_list(query: str) -> str:
    """
    Process the user query through the full pipeline:
    1. Decompose into tasks
    2. Assign tools to tasks
    3. Execute tools
    4. Generate final response
    """
    try:
        # Get available tools and their metadata
        tools_metadata = get_available_tools()
        if not tools_metadata:
            return "I'm sorry, but I don't have any tools available to process your request."

        # Step 1: Decompose query into tasks
        task_prompt = decompose_tasks_prompt.replace("{{query}}", query)
        tasks = call_llm_with_retry(
            role="user",
            content=task_prompt,
            response_model=TaskList
        )

        # Step 2: Assign and execute tools for each task
        results = []
        
        for task in tasks.tasks:
            # Get tool assignment for task
            tool_prompt = assign_tool_prompt.replace(
                "{{task_name}}", task.name
            ).replace(
                "{{task_description}}", task.description
            ).replace(
                "{{tools}}", str(tools_metadata)
            )
            
            tool_assignment = call_llm_with_retry(
                role="user",
                content=tool_prompt,
                response_model=ToolAssignment
            )
            
            # Validate tool assignment before creating ToolInvocation
            if not tool_assignment or not tool_assignment.tool_name:
                continue
                
            # Convert to ToolInvocation with validation
            try:
                tool_invocation = ToolInvocation(
                    tool=tool_assignment.tool_name,
                    tool_input=tool_assignment.parameters
                )
                
                # Execute tool
                tool_result = invoke_tools([tool_invocation])
                
                results.append({
                    "task": task.name,
                    "result": tool_result[0] if tool_result else None
                })
            except ValueError as ve:
                continue
            except Exception as e:
                continue

        # Step 3: Generate final response
        final_prompt = generate_final_response.replace(
            "{{query}}", query
        ).replace(
            "{{results}}", str(results)
        )
        
        final_response = call_llm_with_retry(
            role="user",
            content=final_prompt,
            response_model=FinalResponse
        )
        
        return final_response.content if final_response else "I was unable to process your request properly."
        
    except Exception as e:
        return f"I encountered an error while processing your request: {str(e)}"