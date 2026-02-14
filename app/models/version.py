"""
Repo Version Model
Tracks snapshots of the repository graph, linked to specific git commits.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.utils.db import Base
import uuid

def _uuid() -> str:
    return str(uuid.uuid4())

class RepoVersion(Base):
    __tablename__ = "repo_versions"

    id = Column(String, primary_key=True, default=_uuid)
    repo_id = Column(String, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    scan_id = Column(String, nullable=False, index=True) # Added for lookup
    commit_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Snapshot stats for quick access
    complexity_score = Column(Integer, default=0)
    risk_score = Column(Integer, default=0)

    repository = relationship("Repository", back_populates="versions")
    files = relationship("GraphFile", back_populates="version", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_repo_version_commit", "repo_id", "commit_hash"),
    )
