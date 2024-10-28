# tools/web_functions.py
from utilities.errors import ToolError
import httpx
from bs4 import BeautifulSoup
import re
from typing import Optional, Dict, Any
from .toolbox import tool


class WebError(ToolError):
    """Web-specific errors"""
    def __init__(
        self,
        message: str,
        url: str,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message,
            "get_web_page",
            {
                "url": url,
                "status_code": status_code,
                **(details or {})
            }
        )

@tool('web')
async def get_web_page(url: str, timeout: Optional[int] = 30) -> str:
    """
    Retrieve the full text content of a web page with enhanced error handling.
    
    Args:
        url: Web page URL
        timeout: Request timeout in seconds
        
    Returns:
        Extracted text content from the webpage
        
    Raises:
        WebError: For any web-related errors with detailed context
    """
    
    try:
        # Validate URL format
        if not url.startswith(('http://', 'https://')):
            raise WebError(
                "Invalid URL format",
                url,
                details={"reason": "URL must start with http:// or https://"}
            )

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url,
                    timeout=timeout,
                    headers={
                        "User-Agent": "Mozilla/5.0 (compatible; MyBot/1.0)"
                    },
                    follow_redirects=True
                )
                
                # Check response
                response.raise_for_status()
                
                # Validate content type
                content_type = response.headers.get('content-type', '')
                if not content_type.startswith('text/html'):
                    raise WebError(
                        "Unsupported content type",
                        url,
                        response.status_code,
                        {"content_type": content_type}
                    )
                
                # Parse content
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove unwanted elements
                for element in soup(['script', 'style', 'meta', 'noscript']):
                    element.decompose()
                
                # Extract and clean text
                text = ' '.join(
                    line.strip()
                    for line in soup.get_text(separator=' ').split('\n')
                    if line.strip()
                )
                
                if not text:
                    raise WebError(
                        "No text content found",
                        url,
                        response.status_code
                    )
                
                return text

            except httpx.TimeoutException:
                raise WebError(
                    "Request timed out",
                    url,
                    details={"timeout": timeout}
                )
                
            except httpx.HTTPStatusError as e:
                raise WebError(
                    f"HTTP error occurred",
                    url,
                    e.response.status_code
                )
                
            except httpx.HTTPError as e:
                raise WebError(
                    "HTTP request failed",
                    url,
                    details={"error": str(e)}
                )
                
    except Exception as e:
        if isinstance(e, WebError):
            raise
        raise WebError(
            "Unexpected error occurred",
            url,
            details={"error": str(e)}
        )