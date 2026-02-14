from enum import Enum
from typing import List, Optional
from pydantic import BaseModel

class ScanStatus(str, Enum):
    pending = "pending"
    scanning = "scanning"
    completed = "completed"
    failed = "failed"

class RepoSource(str, Enum):
    local = "local"
    github = "github"

class RepoScanRequest(BaseModel):
    path: str
    source: RepoSource

class ScanStats(BaseModel):
    files: int
    symbols: int
    dependencies: int

class ScanResult(BaseModel):
    scanId: str
    repoId: Optional[str] = None # Added for version lookup
    rootPath: Optional[str] = None # Physical path for agent tools
    status: ScanStatus
    stats: Optional[ScanStats] = None
    error: Optional[str] = None

class Hotspot(BaseModel):
    file: str
    score: int

class RepoHealth(BaseModel):
    repoId: str
    riskScore: int
    circularDependencies: int
    complexityScore: int
    hotspots: List[Hotspot]
