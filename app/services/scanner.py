import os
import asyncio
import uuid
import random
import re
import json
import logging
from typing import Dict, Any, List, Tuple
from app.models.repo import RepoScanRequest, ScanResult, ScanStatus, ScanStats, RepoHealth, Hotspot

logger = logging.getLogger("scanner")

class ScannerService:
    # In-memory storage with persistence
    SCANS: Dict[str, ScanResult] = {}
    HEALTH_DATA: Dict[str, RepoHealth] = {}
    
    SCANS_FILE = os.path.join("data", "scans.json")
    HEALTH_FILE = os.path.join("data", "health.json")

    @staticmethod
    def _save_state():
        try:
            os.makedirs("data", exist_ok=True)
            with open(ScannerService.SCANS_FILE, "w", encoding="utf-8") as f:
                json_data = {k: v.model_dump() for k, v in ScannerService.SCANS.items()}
                json.dump(json_data, f, indent=2)
            with open(ScannerService.HEALTH_FILE, "w", encoding="utf-8") as f:
                json_data = {k: v.model_dump() for k, v in ScannerService.HEALTH_DATA.items()}
                json.dump(json_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save scanner state: {e}")

    @staticmethod
    def _load_state():
        try:
            if os.path.exists(ScannerService.SCANS_FILE):
                with open(ScannerService.SCANS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    ScannerService.SCANS = {k: ScanResult(**v) for k, v in data.items()}
            if os.path.exists(ScannerService.HEALTH_FILE):
                with open(ScannerService.HEALTH_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    ScannerService.HEALTH_DATA = {k: RepoHealth(**v) for k, v in data.items()}
            logger.info(f"Loaded {len(ScannerService.SCANS)} scans and {len(ScannerService.HEALTH_DATA)} health entries.")
        except Exception as e:
            logger.error(f"Failed to load scanner state: {e}")
    @staticmethod
    async def start_scan(request: RepoScanRequest) -> ScanResult:
        scan_id = str(uuid.uuid4())
        
        # Initialize state
        result = ScanResult(
            scanId=scan_id,
            status=ScanStatus.pending
        )
        ScannerService.SCANS[scan_id] = result
        ScannerService._save_state()
        
        # Start background processing
        asyncio.create_task(ScannerService._process_scan(scan_id, request))
        
        return result

    @staticmethod
    async def _process_scan(scan_id: str, request: RepoScanRequest):
        try:
            # Update to scanning
            ScannerService.SCANS[scan_id].status = ScanStatus.scanning
            ScannerService._save_state()
            
            # Simulate processing time for realistic feel on small repos
            await asyncio.sleep(1) 
            
            scan_path = None  # Track for graph build
            
            if request.source == "local":
                if not os.path.exists(request.path):
                    raise ValueError(f"Path not found: {request.path}")
                
                scan_path = request.path
                # Set rootPath for agent
                ScannerService.SCANS[scan_id].rootPath = scan_path
                stats, complexities = ScannerService._scan_directory(request.path)
            
            else:
                # GitHub Cloning
                import shutil
                import tempfile
                import subprocess
                
                # Basic URL validation
                if not request.path.startswith(("http://", "https://")):
                    raise ValueError("Invalid GitHub URL")

                # Permanent storage for scan results
                repo_storage = os.path.join("data", "repos", scan_id)
                os.makedirs(repo_storage, exist_ok=True)
                
                # Clone depth 1 for speed
                try:
                    # Use sync subprocess in thread for Windows compatibility
                    def clone():
                        return subprocess.run(
                            ["git", "clone", "--depth", "1", request.path, repo_storage],
                            capture_output=True,
                            text=True,
                            check=True
                        )
                    
                    await asyncio.to_thread(clone)
                        
                except subprocess.CalledProcessError as e:
                    raise ValueError(f"Failed to clone repository: {e.stderr.strip() if e.stderr else str(e)}")
                except FileNotFoundError:
                    raise ValueError("Git not installed on server")
                
                scan_path = repo_storage
                # Set rootPath for agent
                ScannerService.SCANS[scan_id].rootPath = scan_path
                stats, complexities = ScannerService._scan_directory(scan_path)
                
                # Build graph
                ScannerService.SCANS[scan_id].stats = stats
                ScannerService.SCANS[scan_id].status = ScanStatus.completed
                ScannerService._generate_health(scan_id, stats, complexities)
                
                # Get commit hash for GitHub repo
                commit_hash = await ScannerService._get_git_commit(scan_path)
                await ScannerService._build_graph(scan_id, scan_path, commit_hash)
                return 
            
            ScannerService.SCANS[scan_id].stats = stats
            ScannerService.SCANS[scan_id].status = ScanStatus.completed
            
            # Generate Health Data using real stats
            ScannerService._generate_health(scan_id, stats, complexities)
            
            # Trigger AST graph build for local repos
            if scan_path:
                commit_hash = await ScannerService._get_git_commit(scan_path)
                asyncio.create_task(ScannerService._build_graph(scan_id, scan_path, commit_hash))
            
            ScannerService._save_state()
        except Exception as e:
            logger.exception(f"[{scan_id}] Scan processing failed")
            if scan_id in ScannerService.SCANS:
                ScannerService.SCANS[scan_id].status = ScanStatus.failed
                # Ensure we capture a message even if e is weird
                ScannerService.SCANS[scan_id].error = f"{type(e).__name__}: {str(e)}" if str(e) else f"Internal Error: {type(e).__name__}"

    @staticmethod
    async def _get_git_commit(path: str) -> str:
        """Extract current git commit hash, defaulting to 'unknown'."""
        try:
            import subprocess
            def get_commit():
                return subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=path,
                    capture_output=True,
                    text=True,
                    check=True
                ).stdout.strip()
            
            return await asyncio.to_thread(get_commit)
        except Exception:
            return "unknown"

    @staticmethod
    async def _build_graph(scan_id: str, path: str, commit_hash: str):
        """Run AST graph analysis with its own DB session."""
        try:
            from app.utils.db import AsyncSessionLocal
            from app.services.graph_service import GraphService
            async with AsyncSessionLocal() as session:
                # build_graph now needs to return the repo_id or we need to query it
                # GraphService.build_graph is void. 
                # Let's Modify GraphService.build_graph to return repo_id? 
                # Or just query it here.
                
                await GraphService.build_graph(scan_id, path, commit_hash, session)
                
                # Fetch repo_id to update ScanResult
                from app.models.version import RepoVersion
                from sqlalchemy import select
                result = await session.execute(select(RepoVersion).where(RepoVersion.scan_id == scan_id))
                version = result.scalar_one_or_none()
                
                if version and scan_id in ScannerService.SCANS:
                    ScannerService.SCANS[scan_id].repoId = version.repo_id

                logger.info(f"[{scan_id}] Graph build complete (commit={commit_hash})")
        except Exception as e:
            logger.error(f"[{scan_id}] Graph build failed: {e}")
            if scan_id in ScannerService.SCANS:
                ScannerService.SCANS[scan_id].status = ScanStatus.failed
                ScannerService.SCANS[scan_id].error = f"Graph build failed: {str(e)}"

    @staticmethod
    def _scan_directory(path: str) -> Tuple[ScanStats, List[Tuple[str, int]]]:
        files_count = 0
        symbols_count = 0
        dependencies_count = 0
        file_complexities: List[Tuple[str, int]] = []
        
        for root, dirs, files in os.walk(path):
            # Ignore common ignore dirs
            if any(x in root for x in ["node_modules", ".git", "__pycache__", "venv", "env", "dist", "build"]):
                continue
                
            for file in files:
                file_path = os.path.join(root, file)
                files_count += 1
                
                # Dependency Analysis
                if file == "package.json":
                    dependencies_count += ScannerService._count_npm_deps(file_path)
                elif file == "requirements.txt":
                    dependencies_count += ScannerService._count_pip_deps(file_path)
                    
                # Symbol & Complexity Analysis
                if file.endswith(('.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.java', '.cpp')):
                    syms = ScannerService._count_symbols(file_path)
                    symbols_count += syms
                    
                    complexity = ScannerService._analyze_complexity(file_path)
                    # Store relative path for display
                    rel_path = os.path.relpath(file_path, path)
                    file_complexities.append((rel_path, complexity))
                    
        return ScanStats(
            files=files_count,
            symbols=symbols_count,
            dependencies=dependencies_count
        ), file_complexities

    @staticmethod
    def _count_npm_deps(file_path: str) -> int:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                deps = len(data.get('dependencies', {}))
                dev_deps = len(data.get('devDependencies', {}))
                return deps + dev_deps
        except:
            return 0

    @staticmethod
    def _count_pip_deps(file_path: str) -> int:
        try:
            count = 0
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        count += 1
            return count
        except:
            return 0

    @staticmethod
    def _count_symbols(file_path: str) -> int:
        try:
            count = 0
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            # Regex patterns for common languages
            patterns = [
                r'^def\s+',           # Python func
                r'^class\s+',         # Python/JS/TS class
                r'function\s+',       # JS/TS func
                r'const\s+\w+\s*=\s*(\(|async\s*\()', # JS arrow func
                r'func\s+'            # Go func
            ]
            
            for pat in patterns:
                count += len(re.findall(pat, content, re.MULTILINE))
            return count
        except:
            return 0

    @staticmethod
    def _analyze_complexity(file_path: str) -> int:
        try:
            score = 0
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                score += len(lines)  # LOC is base complexity
                
                # Check indentation depth as proxy for cyclomatic complexity
                for line in lines:
                    indent = len(line) - len(line.lstrip())
                    if indent > 12: # Deep nesting
                        score += 2
                        
                    # Risk patterns
                    if "eval(" in line or "exec(" in line or "dangerouslySetInnerHTML" in line:
                        score += 10
            return score
        except:
            return 0

    @staticmethod
    def _generate_health(scan_id: str, stats: ScanStats, complexities: List[Tuple[str, int]]):
        # Sort files by complexity descending
        complexities.sort(key=lambda x: x[1], reverse=True)
        top_hotspots = complexities[:5]
        
        # Calculate Risk Score (0-100)
        # Higher complexity = Higher risk
        # More deps = Higher risk
        avg_complexity = 0
        if complexities:
            avg_complexity = sum(c[1] for c in complexities) / len(complexities)
            
        risk_score = min(100, int((stats.dependencies * 0.5) + (avg_complexity * 0.2)))
        
        hotspots = [
            Hotspot(file=path, score=score) 
            for path, score in top_hotspots
        ]
        
        ScannerService.HEALTH_DATA[scan_id] = RepoHealth(
            repoId=scan_id,
            riskScore=risk_score,
            circularDependencies=0, # Use dedicated tool for this normally
            complexityScore=int(avg_complexity),
            hotspots=hotspots
        )

    @staticmethod
    def get_status(scan_id: str) -> ScanResult:
        if scan_id not in ScannerService.SCANS:
            raise KeyError("Scan ID not found")
        return ScannerService.SCANS[scan_id]

    @staticmethod
    def get_health(repo_id: str) -> RepoHealth:
        if repo_id not in ScannerService.HEALTH_DATA:
            raise KeyError("Health data not found")
        return ScannerService.HEALTH_DATA[repo_id]

# Load existing state on startup
ScannerService._load_state()
