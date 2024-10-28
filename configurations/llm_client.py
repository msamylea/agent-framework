# configurations/llm_client.py
from openai import AsyncOpenAI
import instructor
from typing import Any, Type, Dict
import asyncio
from pydantic import BaseModel
from utilities.errors import LLMConnectionError, LLMValidationError, LLMError
from config.settings import get_settings


class LLMClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LLMClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        settings = get_settings()
        self.api_key = settings.llm_api_key
        self.base_url = settings.llm_base_url
        self.model = settings.llm_model
        self.max_retries = settings.max_retries
        self.timeout = settings.timeout
        self._create_client()
        self._initialized = True

    def _create_client(self):
        """Create AsyncOpenAI client for Ollama."""
        try:
            self.client = instructor.from_openai(AsyncOpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
            ),
            mode=instructor.Mode.JSON
            )
        except Exception as e:
            raise LLMConnectionError(
                "Failed to initialize LLM client",
                self.base_url,
                details={"error": str(e)}
            )

    async def _process_llm_response(self, response: Dict[str, Any], response_model: Type[BaseModel]) -> Any:
        """Process raw LLM response into structured output."""
        try:
            # Assuming response.choices[0].message.content contains JSON
            content = response.model_dump_json()
            return response_model.model_validate_json(content)
        except Exception as e:
            raise LLMValidationError(
                "Failed to parse LLM response",
                [str(e)],
                details={"response": content}
            )

    async def chat(self, role: str, content: str, response_model: Type[BaseModel]) -> Any:
        """Send a chat completion request to Ollama with structured output handling."""
        attempt = 0
        last_error = None

        while attempt < self.max_retries:
            try:
                # Validate inputs
                if not content.strip():
                    raise LLMValidationError(
                        "Empty content provided",
                        ["content cannot be empty"]
                    )

                # Create completion
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{
                        "role": role,
                        "content": content
                    }],
                    temperature=0.7,
                    response_model=response_model
                )
                
                # Process response into structured output
                return await self._process_llm_response(response, response_model)

            except Exception as e:
                attempt += 1
                
                if attempt >= self.max_retries:
                    if isinstance(e, LLMError):
                        raise
                    raise LLMError(
                        "Failed to get valid response from LLM",
                        details={
                            "error": str(e),
                            "model": self.model,
                            "attempts": attempt
                        }
                    )
                
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)