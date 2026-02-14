import time
import logging
from typing import Dict, Any

from app.adapters.groq import GroqAdapter
from app.adapters.openrouter import OpenRouterAdapter
from app.models.api import ChatRequest

logger = logging.getLogger(__name__)

class RoutingService:
    def __init__(self):
        self.groq = GroqAdapter()
        self.openrouter = OpenRouterAdapter()

    async def route_request(self, request: ChatRequest) -> Dict[str, Any]:
        """
        Routes the request to Groq first, falls back to OpenRouter.
        Returns the raw result dict + metadata for the controller to format.
        """
        start_time = time.time()
        
        # 1. Try Primary (Groq)
        try:
            logger.info("Attempting Primary Provider: Groq")
            result = await self.groq.generate(
                prompt=request.prompt, 
                system_prompt=request.system_prompt,
                model=request.preferred_model if request.preferred_model and "llama" in request.preferred_model else None 
                # Note: Rough heuristic, if user asks for specific model we should check if provider supports it, 
                # but for this strict gateway logic, we try Groq default unless specified.
            )
            result["latency_ms"] = (time.time() - start_time) * 1000
            result["fallback_used"] = False
            return result
            
        except Exception as e:
            logger.error(f"Groq failed: {str(e)}. Initiating Fallback.")
            
            # 2. Fallback (OpenRouter)
            try:
                # Calculate latency so far, but we continue timing
                result = await self.openrouter.generate(
                    prompt=request.prompt,
                    system_prompt=request.system_prompt,
                    # If specific model was requested and failed on Groq, we might want to pass it here 
                    # OR rely on OpenRouter default/mapping. For now, pass preferred if present.
                    model=request.preferred_model
                )
                result["latency_ms"] = (time.time() - start_time) * 1000
                result["fallback_used"] = True
                return result
                
            except Exception as e2:
                logger.critical(f"All providers failed. OpenRouter error: {str(e2)}")
                raise e2
