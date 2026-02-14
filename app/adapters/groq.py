import time
from typing import Optional, Dict, Any
from groq import AsyncGroq
from app.config import get_settings
from app.adapters.base import BaseModelAdapter

settings = get_settings()

class GroqAdapter(BaseModelAdapter):
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.default_model = settings.DEFAULT_MODEL_GROQ

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, model: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Calls Groq API.
        """
        target_model = model or self.default_model
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})

        # We don't catch errors here; we let them propagate to the router for handling/fallback.
        completion = await self.client.chat.completions.create(
            model=target_model,
            messages=messages,
            **kwargs
        )

        return {
            "response": completion.choices[0].message.content,
            "model": target_model,
            "provider": "groq"
        }
