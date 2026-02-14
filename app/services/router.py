"""
Cost-Aware Intelligent Routing Service.

Routing logic:
  1. Score each provider using: latency × weight + fallback_rate × weight + cost × weight
  2. Apply policy overrides:
     - If daily cost > threshold → deprioritize
     - If avg latency > spike threshold → deprioritize
  3. Select lowest-score provider as primary, other as fallback
  4. Log routing decision for observability

All thresholds are configurable via environment variables.
"""

import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime, date

from app.adapters.groq import GroqAdapter
from app.adapters.openrouter import OpenRouterAdapter
from app.models.api import ChatRequest
from app.config import get_settings

logger = logging.getLogger("routing_service")
settings = get_settings()


# ─── In-Memory Cost Tracker ─────────────────────────────

class CostTracker:
    """
    Thread-safe-ish daily cost accumulator per provider.
    Resets automatically on date rollover.
    In production, this would be backed by Redis or DB aggregation.
    """

    def __init__(self):
        self._costs: Dict[str, float] = defaultdict(float)    # provider → daily USD
        self._requests: Dict[str, int] = defaultdict(int)     # provider → request count
        self._latencies: Dict[str, List[float]] = defaultdict(list)  # provider → recent latencies
        self._failures: Dict[str, int] = defaultdict(int)     # provider → failure count
        self._date: date = date.today()

    def _check_rollover(self) -> None:
        """Reset counters at midnight."""
        today = date.today()
        if today != self._date:
            logger.info(f"[CostTracker] Date rollover {self._date} → {today}, resetting counters")
            self._costs.clear()
            self._requests.clear()
            self._latencies.clear()
            self._failures.clear()
            self._date = today

    def record(self, provider: str, cost: float, latency_ms: float) -> None:
        """Record a successful request."""
        self._check_rollover()
        self._costs[provider] += cost
        self._requests[provider] += 1
        # Keep last 50 latencies for avg calculation
        lats = self._latencies[provider]
        lats.append(latency_ms)
        if len(lats) > 50:
            self._latencies[provider] = lats[-50:]

    def record_failure(self, provider: str) -> None:
        """Record a provider failure."""
        self._check_rollover()
        self._failures[provider] += 1

    def get_daily_cost(self, provider: str) -> float:
        self._check_rollover()
        return self._costs.get(provider, 0.0)

    def get_avg_latency(self, provider: str) -> float:
        self._check_rollover()
        lats = self._latencies.get(provider, [])
        return sum(lats) / len(lats) if lats else 0.0

    def get_fallback_rate(self, provider: str) -> float:
        self._check_rollover()
        total = self._requests.get(provider, 0) + self._failures.get(provider, 0)
        if total == 0:
            return 0.0
        return self._failures.get(provider, 0) / total

    def get_total_requests(self, provider: str) -> int:
        self._check_rollover()
        return self._requests.get(provider, 0)

    def get_snapshot(self) -> Dict[str, Any]:
        """Full snapshot for /metrics/cost endpoint."""
        self._check_rollover()
        providers = set(list(self._costs.keys()) + list(self._requests.keys()))
        result = {}
        for p in providers:
            result[p] = {
                "daily_cost_usd": round(self._costs.get(p, 0.0), 6),
                "requests_today": self._requests.get(p, 0),
                "failures_today": self._failures.get(p, 0),
                "avg_latency_ms": round(self.get_avg_latency(p), 2),
                "fallback_rate": round(self.get_fallback_rate(p), 4),
            }
        return result


# Singleton tracker
cost_tracker = CostTracker()


# ─── Provider Scoring ───────────────────────────────────

@dataclass
class ProviderScore:
    name: str
    score: float
    reason: str
    cost_per_1k: float
    daily_cost: float
    avg_latency: float
    fallback_rate: float
    deprioritized: bool = False


def _estimate_cost(tokens: int, cost_per_1k: float) -> float:
    """Estimate USD cost from token count."""
    return (tokens / 1000.0) * cost_per_1k


def _score_provider(
    name: str,
    cost_per_1k: float,
    daily_limit: float,
) -> ProviderScore:
    """
    Compute provider score. Lower = better.
    
    score = (avg_latency_normalized * weight_latency) 
          + (fallback_rate * weight_fallback) 
          + (cost_per_1k * weight_cost * 1000)
    
    Apply penalty if daily cost exceeds limit or latency spikes.
    """
    avg_lat = cost_tracker.get_avg_latency(name)
    fb_rate = cost_tracker.get_fallback_rate(name)
    daily_cost = cost_tracker.get_daily_cost(name)

    # Normalize latency to 0-1 range (5000ms = 1.0)
    lat_norm = min(avg_lat / 5000.0, 2.0)

    base_score = (
        lat_norm * settings.WEIGHT_LATENCY +
        fb_rate * settings.WEIGHT_FALLBACK +
        cost_per_1k * settings.WEIGHT_COST * 1000
    )

    reason_parts = []
    deprioritized = False

    # Policy: Cost ceiling
    if daily_cost >= daily_limit:
        base_score += 10.0  # Massive penalty
        deprioritized = True
        reason_parts.append(f"cost_exceeded(${daily_cost:.4f}>=${daily_limit})")

    # Policy: Latency spike
    if avg_lat > settings.LATENCY_SPIKE_MS:
        base_score += 5.0
        deprioritized = True
        reason_parts.append(f"latency_spike({avg_lat:.0f}ms>{settings.LATENCY_SPIKE_MS}ms)")

    reason = ", ".join(reason_parts) if reason_parts else "nominal"

    return ProviderScore(
        name=name,
        score=round(base_score, 4),
        reason=reason,
        cost_per_1k=cost_per_1k,
        daily_cost=daily_cost,
        avg_latency=avg_lat,
        fallback_rate=fb_rate,
        deprioritized=deprioritized,
    )


# ─── Routing Service ───────────────────────────────────

class RoutingService:
    def __init__(self):
        self.providers = {
            "groq": GroqAdapter(),
            "openrouter": OpenRouterAdapter(),
        }
        self.cost_rates = {
            "groq": settings.COST_PER_1K_GROQ,
            "openrouter": settings.COST_PER_1K_OPENROUTER,
        }
        self.daily_limits = {
            "groq": settings.DAILY_COST_LIMIT_GROQ,
            "openrouter": settings.DAILY_COST_LIMIT_OPENROUTER,
        }

    def _evaluate_policy(self) -> List[ProviderScore]:
        """Score all providers and return sorted (best first)."""
        scores = []
        for name in self.providers:
            ps = _score_provider(
                name=name,
                cost_per_1k=self.cost_rates[name],
                daily_limit=self.daily_limits[name],
            )
            scores.append(ps)

        scores.sort(key=lambda s: s.score)
        return scores

    async def route_request(self, request: ChatRequest) -> Dict[str, Any]:
        """
        Cost-aware intelligent routing.
        Scores providers → tries best first → falls back to next.
        Returns result dict with cost metadata.
        """
        start_time = time.time()
        
        # 1. Check for explicit provider override
        if request.preferred_provider and request.preferred_provider in self.providers:
            scores = [
                # Create a dummy score for the preferred provider
                _score_provider(
                    name=request.preferred_provider,
                    cost_per_1k=self.cost_rates[request.preferred_provider],
                    daily_limit=self.daily_limits[request.preferred_provider],
                )
            ]
            logger.info(f"[Routing] Explicit provider requested: {request.preferred_provider}")
        else:
            # 2. Evaluate policy for auto-routing
            scores = self._evaluate_policy()
            logger.info(
                f"[Routing] Provider scores: "
                + ", ".join(f"{s.name}={s.score}({'⚠' if s.deprioritized else '✓'})" for s in scores)
            )

        last_error: Optional[Exception] = None
        routing_reason = f"policy:{scores[0].name}({scores[0].reason})"

        for i, ps in enumerate(scores):
            provider_name = ps.name
            adapter = self.providers[provider_name]

            try:
                logger.info(f"[Routing] Attempting {provider_name} (score={ps.score}, reason={ps.reason})")

                result = await adapter.generate(
                    prompt=request.prompt,
                    system_prompt=request.system_prompt,
                    model=request.preferred_model if request.preferred_model else None,
                )

                latency_ms = (time.time() - start_time) * 1000
                tokens = result.get("tokens_used", 0)
                est_cost = _estimate_cost(tokens, self.cost_rates[provider_name])

                # Record success in cost tracker
                cost_tracker.record(provider_name, est_cost, latency_ms)

                result["latency_ms"] = latency_ms
                result["fallback_used"] = i > 0
                result["tokens_used"] = tokens
                result["estimated_cost"] = round(est_cost, 8)
                result["routing_reason"] = routing_reason

                logger.info(
                    f"[Routing] ✓ {provider_name} | {latency_ms:.0f}ms | "
                    f"{tokens} tokens | ${est_cost:.6f} | "
                    f"daily_total=${cost_tracker.get_daily_cost(provider_name):.4f}"
                )

                return result

            except Exception as e:
                cost_tracker.record_failure(provider_name)
                logger.error(f"[Routing] ✗ {provider_name} failed: {e}")
                last_error = e
                routing_reason = f"fallback:{provider_name}_failed→{scores[min(i+1, len(scores)-1)].name}"
                continue

        # All providers failed
        logger.critical("[Routing] All providers exhausted.")
        raise last_error or RuntimeError("All providers unavailable")
