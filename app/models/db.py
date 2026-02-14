from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Integer, Boolean, Text
from app.utils.db import Base

class RequestLog(Base):
    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True, index=True)
    prompt = Column(Text, nullable=False)
    provider_used = Column(String, nullable=False)
    model_used = Column(String, nullable=False)
    latency_ms = Column(Float, nullable=False)
    fallback_used = Column(Boolean, default=False)
    tokens_used = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0.0)
    routing_reason = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
