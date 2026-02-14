from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, desc
from app.models.db import RequestLog
from app.models.metrics import MetricsSummary, ProviderSplit, TimeRange

class MetricsService:
    @staticmethod
    async def get_summary(db: AsyncSession, time_range: TimeRange) -> MetricsSummary:
        # Determine start time
        now = datetime.utcnow()
        if time_range == TimeRange.last_1h:
            start_time = now - timedelta(hours=1)
        elif time_range == TimeRange.last_24h:
            start_time = now - timedelta(hours=24)
        elif time_range == TimeRange.last_7d:
            start_time = now - timedelta(days=7)
        else:
            start_time = now - timedelta(hours=24)

        # Base Filter
        base_filter = RequestLog.timestamp >= start_time

        # 1. Main Aggregates (Count, Avg Latency, Fallback Count)
        # Using separate queries for clarity and driver compatibility, though could be combined.
        # Fallback count logic: SUM(case when fallback_used then 1 else 0 end)
        
        agg_query = select(
            func.count(RequestLog.id).label("total"),
            func.avg(RequestLog.latency_ms).label("avg_latency"),
            func.sum(case((RequestLog.fallback_used == True, 1), else_=0)).label("fallback_count")
        ).where(base_filter)
        
        result = await db.execute(agg_query)
        agg_data = result.first()
        
        total_requests = agg_data.total or 0
        avg_latency = float(agg_data.avg_latency or 0.0)
        fallback_count = agg_data.fallback_count or 0
        
        fallback_rate = 0.0
        if total_requests > 0:
            fallback_rate = (fallback_count / total_requests) * 100

        # 2. Provider Split
        split_query = select(
            RequestLog.provider_used,
            func.count(RequestLog.id)
        ).where(base_filter).group_by(RequestLog.provider_used)
        
        split_result = await db.execute(split_query)
        splits = split_result.all()
        
        provider_data = []
        for provider, count in splits:
            percentage = (count / total_requests * 100) if total_requests > 0 else 0
            provider_data.append(ProviderSplit(
                provider=provider,
                count=count,
                percentage=round(percentage, 2)
            ))

        # 3. P95 Latency
        # Hybrid Approach: Check if Postgres for optimized quantile, else python-side
        dialect_name = db.bind.dialect.name
        p95_latency = 0.0

        if dialect_name == "postgresql" and total_requests > 0:
            # Clean High-performance Postgres path
            p95_stmt = select(
                func.percentile_cont(0.95).within_group(RequestLog.latency_ms)
            ).where(base_filter)
            p95_res = await db.execute(p95_stmt)
            p95_latency = float(p95_res.scalar() or 0.0)
        elif total_requests > 0:
            # SQLite / Generic Fallback: Fetch all latencies and compute in memory
            # Note: For massive scale, this shouldn't be used, but fine for local/sqlite scenario.
            lat_stmt = select(RequestLog.latency_ms).where(base_filter).order_by(RequestLog.latency_ms)
            lat_res = await db.execute(lat_stmt)
            latencies = [row[0] for row in lat_res.all()]
            
            if latencies:
                # Poor man's percentile without numpy dependency to keep it light
                index = int(len(latencies) * 0.95)
                # Ensure index is within bounds
                index = min(index, len(latencies) - 1)
                p95_latency = float(latencies[index])

        return MetricsSummary(
            total_requests=total_requests,
            avg_latency_ms=round(avg_latency, 2),
            p95_latency_ms=round(p95_latency, 2),
            fallback_rate_percent=round(fallback_rate, 2),
            provider_split=provider_data
        )
