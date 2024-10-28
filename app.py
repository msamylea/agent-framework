# app.py
from pathlib import Path
import yaml
import asyncio
from agents.setup import setup_agent_system


def load_app_config():
    """Load application configuration"""
    config_path = Path(__file__).parent / "config" / "app.yaml"
    
    if not config_path.exists():
        raise FileNotFoundError(f"App config file not found: {config_path}")
        
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
            return config
    except Exception as e:
        raise ValueError(f"Error loading app config: {str(e)}")

async def run_chat_agent():
    """Initialize and run chat agent from configuration"""
    try:
        print("Initializing chat system...")
        
        # Load app configuration
        config = load_app_config()
        
        # Set up agent system
        print("Setting up agent system...")
        director = await setup_agent_system()
        
        # Get the configured chat agent for command handling only
        agent_name = config.get("default_agent", "ChatAgent")
        chat_agent = next(
            (agent for agent in director.agents if agent.name == agent_name),
            director.agents[0] if director.agents else None
        )
        
        if not chat_agent:
            raise ValueError("No suitable agent found")
            
        print("\nType 'exit' to end the conversation.")
        print("Type 'help' to see available commands.")
        
        # Start conversation loop
        while True:
            try:
                user_input = input("\nUser: ").strip()
                
                if user_input.lower() == 'exit':
                    print("Ending conversation. Goodbye!")
                    break
                    
                if user_input.lower() == 'help':
                    print("\nAvailable commands:")
                    print("- exit: End the conversation")
                    print("- help: Show this help message")
                    print("- capabilities: List agent capabilities")
                    print("- clear: Clear conversation history")
                    continue
                    
                if user_input.lower() == 'capabilities':
                    print("\nAgent capabilities:")
                    for cap in chat_agent.capabilities:
                        print(f"\n{cap.name}:")
                        print(f"  Description: {cap.description}")
                        print("  Parameters:")
                        for param_name, param_info in cap.parameters.items():
                            default = f" (default: {param_info['default']})" if 'default' in param_info else ""
                            print(f"    - {param_name}: {param_info['description']}{default}")
                    continue
                    
                if user_input.lower() == 'clear':
                    chat_agent.clear_history()
                    print("Conversation history cleared.")
                    continue
                
                if not user_input:
                    continue
                    
                # Process user input using Director
                print("Processing request...")
                response = await director.process_request(user_input)

                # Show response
                if isinstance(response, dict):
                    formatted_output = response.get('formatted_output')
                    if formatted_output:
                        print("\nAgent Response:")
                        print(formatted_output)
                    elif 'error' in response:
                        print(f"\nError: {response['error']}")

                # Show task details
                if isinstance(response, dict) and 'all_results' in response:
                    print("\nTask Execution Summary:")
                    for result in response['all_results']:
                        task = result.get('task', {})
                        print(f"- {task.get('name', 'Unknown task')}")
                        print(f"  Status: {result.get('result', {}).get('status', 'unknown')}")
                        if 'error' in result:
                            print(f"  Error: {result['error']}")
                
            except Exception as e:
                print(f"\nAgent: I encountered an error while processing your request: {str(e)}")

    except Exception as e:
        print(f"Error initializing chat: {str(e)}")
        return

def main():
    """Main entry point with proper error handling"""
    try:
        print("Starting AI Chat Assistant...")
        
        # Run the async chat agent
        asyncio.run(run_chat_agent())
        
    except KeyboardInterrupt:
        print("\nChat session terminated by user.")
    except Exception as e:
        print(f"Fatal error: {str(e)}")
    finally:
        print("AI Chat Assistant terminated.")

if __name__ == "__main__":
    main()