from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class BaseModelAdapter(ABC):
    """
    Abstract base class for all LLM providers.
    Enforces a common interface for generation.
    """

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Generates text from the provider.
        
        Args:
            prompt: User input
            system_prompt: Optional system instruction
            **kwargs: Extra model params
            
        Returns:
            Dict containing:
                - response: str
                - model: str
                - provider: str
        """
        pass
