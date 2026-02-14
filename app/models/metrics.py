from enum import Enum
from typing import List, Dict
from pydantic import BaseModel, Field

class TimeRange(str, Enum):
    last_1h = "last_1h"
    last_24h = "last_24h"
    last_7d = "last_7d"

class ProviderSplit(BaseModel):
    provider: str
    count: int
    percentage: float

class MetricsSummary(BaseModel):
    total_requests: int
    avg_latency_ms: float
    p95_latency_ms: float
    fallback_rate_percent: float
    provider_split: List[ProviderSplit]
