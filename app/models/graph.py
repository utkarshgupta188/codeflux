"""
SQLAlchemy ORM models for the structural code graph.

Tables: repositories, graph_files, symbols, edges
All use UUID primary keys for cross-reference stability.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey, Enum as SAEnum, Text, Index
)
from sqlalchemy.orm import relationship
from app.utils.db import Base
import enum


# ─── Enums ───────────────────────────────────────────────

class SymbolType(str, enum.Enum):
    module = "module"
    class_ = "class"
    function = "function"
    method = "method"
    import_ = "import"


class EdgeRelation(str, enum.Enum):
    defines = "defines"
    calls = "calls"
    imports = "imports"


# ─── Tables ──────────────────────────────────────────────

def _uuid() -> str:
    return str(uuid.uuid4())



class Repository(Base):
    __tablename__ = "repositories"

    id = Column(String, primary_key=True, default=_uuid)
    scan_id = Column(String, nullable=False, unique=True, index=True)
    root_path = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    versions = relationship("RepoVersion", back_populates="repository", cascade="all, delete-orphan")


class GraphFile(Base):
    __tablename__ = "graph_files"

    id = Column(String, primary_key=True, default=_uuid)
    # version_id replaces repo_id as the parent
    version_id = Column(String, ForeignKey("repo_versions.id", ondelete="CASCADE"), nullable=False)
    path = Column(Text, nullable=False)          # relative to repo root
    module_name = Column(String, nullable=True)   # dotted: app.services.scanner

    version = relationship("RepoVersion", back_populates="files")
    symbols = relationship("Symbol", back_populates="file", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_graphfile_version", "version_id"),
    )



class Symbol(Base):
    __tablename__ = "symbols"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    qualified_name = Column(String, nullable=True)   # e.g. MyClass.my_method
    type = Column(SAEnum(SymbolType), nullable=False)
    file_id = Column(String, ForeignKey("graph_files.id", ondelete="CASCADE"), nullable=False)
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)

    file = relationship("GraphFile", back_populates="symbols")

    __table_args__ = (
        Index("ix_symbol_file", "file_id"),
        Index("ix_symbol_name", "name"),
    )


class Edge(Base):
    __tablename__ = "edges"

    id = Column(String, primary_key=True, default=_uuid)
    source_id = Column(String, ForeignKey("symbols.id", ondelete="CASCADE"), nullable=False)
    target_id = Column(String, ForeignKey("symbols.id", ondelete="CASCADE"), nullable=False)
    relation = Column(SAEnum(EdgeRelation), nullable=False)

    source = relationship("Symbol", foreign_keys=[source_id])
    target = relationship("Symbol", foreign_keys=[target_id])

    __table_args__ = (
        Index("ix_edge_source", "source_id"),
        Index("ix_edge_target", "target_id"),
    )
