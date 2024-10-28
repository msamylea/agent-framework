# from g4f.client import Client

# client = Client()
# response = client.chat.completions.create(
#     model="nemotron-70b",
#     messages=[{"role": "user", "content": "Give me the code to create a flexible, configurable agentic framework for llms"}],
#     # Add any other necessary parameters
# )
# print(response.choices[0].message.content)


# # tools/search_functions.py
from duckduckgo_search import DDGS




def ddg_search(topic: str, max_results: int = 10) -> str:
    """
    Search DuckDuckGo and return results.
    
    Args:
        topic: Search query string
        max_results: Maximum number of results to return
        
    Returns:
        String containing formatted search results
    """
    
    try:
        ddgs = DDGS()
        results = list(ddgs.text(str(topic), max_results=int(max_results)))
        formatted_results = []
        print("Results: ", results)
        if not results:
            return f"No results found for: {topic}"
        
        for result in results:
            formatted_results.append(
                f"Title: {result['title']}\n"
                f"URL: {result['link']}\n"
                f"Summary: {result['body']}\n"
                "---"
            )
        
        return "\n\n".join(formatted_results)
    except Exception as e:
        return f"Error performing search: {str(e)}"
    

print(ddg_search("Python"))