# agents/setup.py
from typing import Dict
import yaml
from pathlib import Path
from configurations.llm_client import LLMClient
from tools.toolbox import tool_registry
from .models import AgentCapability
from .director import AgentDirector
from .base import Agent


def load_capabilities_config() -> Dict:
    """Load capabilities and agent configurations"""
    config_path = Path(__file__).parent / "config" / "capabilities.yaml"
    
    if not config_path.exists():
        raise FileNotFoundError(f"Capabilities config file not found: {config_path}")
        
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
            return config
    except Exception as e:
        raise ValueError(f"Error loading capabilities config: {str(e)}")

async def setup_agent_system() -> AgentDirector:
    """Set up the agent system from configuration"""
    try:
        # Initialize components
        director = AgentDirector()
        llm_client = LLMClient()
        director.llm = llm_client

        # Load configurations
        config = load_capabilities_config()
        
        # Get available tools and their types
        available_tools = tool_registry.list_tools()
        available_types = {
            tool_config.get("function_type") 
            for tool_config in available_tools.values()
        }

        created_agents = []
        for agent_name, agent_config in config["agents"].items():
            
            agent_capabilities = []
            for cap_name in agent_config["capabilities"]:
                if cap_name not in config["capabilities"]:
                    continue
                    
                cap_config = config["capabilities"][cap_name]
                
                # Verify required function types are available
                missing_types = [
                    ft for ft in cap_config["function_types"] 
                    if ft not in available_types
                ]
                
                if missing_types:
                    continue

                agent_capabilities.append(AgentCapability(**cap_config))

            # Create agent if it has valid capabilities
            if agent_capabilities:
                agent = Agent(
                    name=agent_name,
                    description=agent_config["description"],
                    capabilities=agent_capabilities,
                    llm=llm_client
                )

                # Add tools that match the agent's required function types
                required_types = set()
                for cap in agent_capabilities:
                    required_types.update(cap.function_types)
                    
                agent_tools = []
                for tool_name, tool_config in available_tools.items():
                    if tool_config.get("function_type") in required_types:
                        agent_tools.append({
                            "name": tool_name,
                            "metadata": tool_config
                        })

                agent.add_tools(agent_tools)
                director.register_agent(agent)

                created_agents.append({
                    "name": agent_name,
                    "description": agent_config["description"],
                    "capabilities": agent_capabilities
                })

            

            else:
                return None
            
        print("I have created the following agents:")
        print("=" * 30)
        print("\n")
        for agent in created_agents:
            print(f"Agent: {agent['name']}")
            print(f"Description: {agent['description']}")
            print("Capabilities:")
            for cap in agent["capabilities"]:
                print(f"- {cap.name}: {cap.description}")
            print("\n")
        print("=" * 30)

        return director

    except Exception as e:
        raise ValueError(f"Error setting up agent system: {str(e)}")