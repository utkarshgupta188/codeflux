"""
Pydantic response schemas for the graph API.
"""

from typing import List, Optional
from pydantic import BaseModel


class SymbolNode(BaseModel):
    id: str
    name: str
    qualified_name: Optional[str] = None
    type: str            # module | class | function | method | import
    file: str            # relative path
    start_line: int
    end_line: int


class GraphEdge(BaseModel):
    source_id: str
    target_id: str
    relation: str        # defines | calls | imports


class CyclePath(BaseModel):
    cycle: List[str]     # ordered list of names forming the cycle
    type: str            # "import" or "call"


class GraphResponse(BaseModel):
    scan_id: str
    total_files: int
    total_symbols: int
    total_edges: int
    nodes: List[SymbolNode]
    edges: List[GraphEdge]
    circular_dependencies: List[CyclePath]
