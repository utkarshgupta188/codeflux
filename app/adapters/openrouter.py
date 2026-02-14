import httpx
from typing import Optional, Dict, Any
from app.config import get_settings
from app.adapters.base import BaseModelAdapter

settings = get_settings()

class OpenRouterAdapter(BaseModelAdapter):
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.base_url = "https://openrouter.ai/api/v1"
        self.default_model = settings.DEFAULT_MODEL_OPENROUTER

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, model: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Calls OpenRouter API using standard HTTPX (lighter than full OpenAI client for this case).
        """
        target_model = model or self.default_model
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://ai-gateway.internal", # Required by OpenRouter
            "X-Title": "AI Gateway",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": target_model,
            "messages": messages,
            **kwargs
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=30.0
            )
            resp.raise_for_status()
            data = resp.json()
            
            content = data["choices"][0]["message"]["content"]
            
            return {
                "response": content,
                "model": target_model,
                "provider": "openrouter"
            }
