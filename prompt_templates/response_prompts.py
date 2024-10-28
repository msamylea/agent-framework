
decompose_tasks_prompt = """Analyze this user request and break it down into step-by-step tasks.
For each task, determine which tools would be most appropriate.

User Request: {{query}}

The available tools are:
{{tools_info}}

Break this into sequential tasks, where each task builds on the previous ones.
Return a list of tasks in this exact format:
{
    "tasks": [
        {
            "name": "task_name",
            "description": "what needs to be done",
            "tool": "name_of_tool_to_use",
            "parameters": {
                "param1": "value1"
            }
           ]
}

For the example query "Research meteorology then write weather code":
1. First task should use ddg_search to gather meteorology information
2. Second task should use execute_python_code to write code based on the research

Each task should have all necessary information to execute."""

assign_tool_prompt = '''You are a JSON response generator. Given user input, choose the best tool to handle the request and return a properly formatted JSON response.

Available tools:
{{tools_info}}

User request: {{task_input}}


Response must be VALID JSON in exactly this format:
{
    "tool_name": "name_of_tool",
    "parameters": {
        "param1": "value1"
    }
}


Respond with ONLY the JSON. No other text.'''

generate_final_response = """Based on the search results and any other tool outputs, create a natural language response.

Original Query: {{query}}
Results: {{results}}

Return a JSON object with this exact structure:
{
    "content": "Your complete response here, summarizing the results in a natural way"
}

If the results indicate no data was found or errors occurred, acknowledge this and explain what alternative sources the user might consult."""

get_agent_capabilities = """
Given this user request, break it down into specific tasks that can be handled by our agents.
            
            User Request: {{request}}

            Available Capabilities:
            {{available_capabilities}}

            For each task, specify:
            1. A descriptive name
            2. Required capabilities from the available list
            3. Specific parameters needed for those capabilities
            4. A clear description of what needs to be done

            Return a list of tasks in this exact format:
            [
                {
                    "name": "task_name",
                    "description": "what needs to be done",
                    "required_capabilities": ["capability_name"],
                    "parameters": {
                        "capability_name": {
                            "param1": value1,
                            "param2": value2
                        }
                    }
                }
            ]


"""


summarize_final_response = """

Based on these tool results and the user's original request, provide a clear summary:
            User's Request: 
            {{user_input}}

            Tool Results:
            {{formatted_results}}


            Create a full response that:
            1. Summarizes the key information that answers the user's question
            2. Notes any limitations or issues
            3. Suggests follow-up actions if appropriate
            4. If code is provided, ensure it is formatted correctly
            5. Provide references or citations if needed, including any relevant URLs that were part of the results

"""

generate_code = """Based on these research results about meteorology and weather forecasting,
                    write Python code that meets this goal:
                    {{task_description}}

                    Context from previous research:
                    {{previous_results}}

                    Write concise, well-documented Python code that solves this task.
                    The code must be complete and executable.
                    Do not include string literals of code or code generation functions
                    Only return the actual Python code, no additional text or explanation.
                    Prefer using standard library modules where possible.
                    Always include a print statement where poosible to show the output.

                    Write the actual implementation code that will be executed.
                    NO code generation functions or string templates.

                    Return the Python code in this format:
                    {
                        "code": "your_python_code_here"
                    }

            """

handle_code_error = """
            Code was generated for a task based on a user's request, but an error occurred when executing the code.
            Your job is to review the code and the error and return corrected code.

            Task: {{task_description}}
            Error: {{error_message}}
            Code: {{code}}

            Review the code and error message, then correct the code as needed.

            Return the corrected code in this format:
            {
                "code": "your_corrected_python_code_here"
            }

"""
            