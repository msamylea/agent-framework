# tools/search_functions.py
from duckduckgo_search import DDGS
from .toolbox import tool


@tool('search')
async def ddg_search(topic: str, max_results: int = 5) -> str:
    """
    Search DuckDuckGo and return results. Returns only basic information and urls.
    If more data is needed, use web search instead or use it after this function with one of the urls.
    
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
        
        if not results:
            return f"No results found for: {topic}"
        
        for result in results:
            formatted_results.append(
                f"Title: {result['title']}\n"
                f"URL: {result['href']}\n"
                f"Summary: {result['body']}\n"
                "---"
            )
        
        return "\n\n".join(formatted_results)
    except Exception as e:
        return f"Error performing search: {str(e)}"