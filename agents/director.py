# agents/director.py
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from schemas.resp_formats import TaskList
from prompt_templates.response_prompts import decompose_tasks_prompt
from tools.toolbox import tool_registry
from .models import AgentCapability 
from .base import Agent
from communications.output_manager import OutputManager


class AgentDirector(BaseModel):
    """Coordinates multiple agents"""
    agents: List[Agent] = Field(default_factory=list)
    llm: Any = None
    output_manager: OutputManager = None  # Define the field
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.output_manager is None:  # Initialize if not provided
            self.output_manager = OutputManager()

    def register_agent(self, agent: Agent):
        """Register a new agent"""
        self.agents.append(agent)

    async def process_request(self, request: str) -> Dict[str, Any]:
        """Process a request using appropriate agents"""
        request_id = str(hash(request))
        self.output_manager.start_request(request_id)

        try:
            # Get tasks from request
            tasks = await self._decompose_request(request)
            print(f"\nDecomposed into {len(tasks)} tasks:")
            for i, task in enumerate(tasks, 1):
                print(f"{i}. {task.get('name')}: {task.get('description')}")
            
            if not tasks:
                self.output_manager.add_result(
                    task_id=request_id,
                    status="error",
                    result=None,
                    error="Could not understand how to process this request"
                )
                return {
                    "status": "error",
                    "error": "Could not understand how to process this request",
                    "formatted_output": self.output_manager.format_output(response="Could not understand how to process this request")
                }

            all_results = []
            task_outputs = {}  # Store outputs for dependency handling

            # Execute tasks in sequence
            for task in tasks:
                print(f"\n=== Executing Task: {task.get('name')} ===")
                print(f"Description: {task.get('description')}")
                
                # Handle dependencies
                if 'depends_on' in task:
                    for dep_id in task['depends_on']:
                        if dep_id in task_outputs:
                            task['parameters']['previous_results'] = task_outputs[dep_id]

                # Find suitable agent
                agent = self._find_best_agent(task)
                if agent:
                    try:
                        # Use new execute_task_and_format method
                        result = await agent.execute_task_and_format(task, request)
                        task_outputs[task['id']] = result.get('task_output')
                        
                        self.output_manager.add_result(
                            task_id=task.get('id', 'unknown'),
                            status=result.get('status', 'error'),
                            result=result.get('task_output', []),
                            agent_name=agent.name,
                            error=result.get('error')
                        )
                        all_results.append({
                            'task': task,
                            'result': result,
                            'agent': agent.name
                        })
                    except Exception as e:
                        self.output_manager.add_result(
                            task_id=task.get('id', 'unknown'),
                            status="error",
                            result=None,
                            agent_name=agent.name,
                            error=str(e)
                        )
                else:
                    self.output_manager.add_result(
                        task_id=task.get('id', 'unknown'),
                        status="error",
                        result=None,
                        error="No suitable agent found"
                    )

            summary = self.output_manager.get_summary()
            return {
                "status": summary.overall_status,
                "formatted_output": self.output_manager.format_output(summary),
                "raw_summary": summary.model_dump(),
                "all_results": all_results
            }

        except Exception as e:
            self.output_manager.add_result(
                task_id=request_id,
                status="error",
                result=None,
                error=str(e)
            )
            return {
                "status": "error",
                "error": str(e),
                "formatted_output": self.output_manager.format_output(response=str(e))
            }
    async def _decompose_request(self, request: str) -> List[Dict[str, Any]]:
        """Break request into tasks using LLM"""
        try:
            # Get both capabilities and tools info
            available_capabilities = self._get_available_capabilities()
            available_tools = tool_registry.list_tools()
            
            print("AVAILABLE TOOLS: ", available_tools)
            # Format tools info
            tools_info = []
            for name, config in available_tools.items():
                tools_info.append(f"""
                    Tool: {name}
                    Description: {config['description']}
                    Type: {config['function_type']}
                    Parameters: {', '.join(config['parameters'].keys())}
                """)
            
            # Create comprehensive prompt
            prompt = decompose_tasks_prompt.replace(
                "{{query}}", request
            ).replace(
                "{{tools_info}}", "\n".join(tools_info)
            )
            
            # Add capabilities information
            prompt += "\n\nAvailable Agent Capabilities:\n"
            prompt += available_capabilities

            # Get LLM response
            response = await self.llm.chat(
                role="user",
                content=prompt,
                response_model=TaskList
            )

            print("LLM Response: ", response)
            # Add IDs and validate tasks
            tasks = []
            for i, task in enumerate(response.tasks):
                task_dict = task.dict()
                # Add task ID if not present
                if 'id' not in task_dict:
                    task_dict['id'] = f"task_{i}"
                
                # Validate tool exists
                if task_dict.get('tool') not in available_tools:
                    print(f"Warning: Tool {task_dict.get('tool')} not found, skipping task")
                    continue
                    
                # Add capabilities based on tool type
                tool_type = available_tools[task_dict['tool']]['function_type']
                task_dict['required_capabilities'] = [
                    cap.name for cap in self._get_capabilities_for_tool_type(tool_type)
                ]
                
                tasks.append(task_dict)

            return tasks

        except Exception as e:
            print(f"Error decomposing request: {str(e)}")
            return []

    def _get_capabilities_for_tool_type(self, tool_type: str) -> List[AgentCapability]:
        """Get capabilities that can handle a specific tool type"""
        matching_capabilities = []
        for agent in self.agents:
            for capability in agent.capabilities:
                if tool_type in capability.function_types:
                    matching_capabilities.append(capability)
        return matching_capabilities
            
    def _find_best_agent(self, task: Dict[str, Any]) -> Optional[Agent]:
        """Find the most suitable agent for a task"""
        suitable_agents = [
            agent for agent in self.agents 
            if agent.can_handle_task(task)
        ]
        
        if not suitable_agents:
            return None
            
        # If multiple agents can handle the task, prefer specialized agents over general ones
        return min(suitable_agents, key=lambda a: len(a.capabilities))

    def _get_available_capabilities(self) -> str:
        """Get formatted string of all available capabilities"""
        capabilities = set()
        for agent in self.agents:
            for capability in agent.capabilities:
                capabilities.add(f"""
                {capability.name}:
                - Description: {capability.description}
                - Parameters: {capability.parameters}
                """)
        
        return "\n".join(capabilities)