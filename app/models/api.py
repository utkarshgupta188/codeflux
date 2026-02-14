from pydantic import BaseModel, Field
from typing import Optional

class ChatRequest(BaseModel):
    prompt: str = Field(..., description="The input user prompt")
    task_type: Optional[str] = Field(None, description="Type of task (e.g., summary, extraction)")
    preferred_model: Optional[str] = Field(None, description="Explicit model override")
    system_prompt: Optional[str] = Field(None, description="System instruction")

class ChatResponse(BaseModel):
    response: str
    model_used: str
    provider_used: str
    latency_ms: float
