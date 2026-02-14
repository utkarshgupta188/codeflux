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

# In-memory storage for V1
SCANS: Dict[str, ScanResult] = {}
HEALTH_DATA: Dict[str, RepoHealth] = {}

class ScannerService:
    @staticmethod
    async def start_scan(request: RepoScanRequest) -> ScanResult:
        scan_id = str(uuid.uuid4())
        
        # Initialize state
        result = ScanResult(
            scanId=scan_id,
            status=ScanStatus.pending
        )
        SCANS[scan_id] = result
        
        # Start background processing
        asyncio.create_task(ScannerService._process_scan(scan_id, request))
        
        return result

    @staticmethod
    async def _process_scan(scan_id: str, request: RepoScanRequest):
        try:
            # Update to scanning
            SCANS[scan_id].status = ScanStatus.scanning
            
            # Simulate processing time for realistic feel on small repos
            await asyncio.sleep(1) 
            
            scan_path = None  # Track for graph build
            
            if request.source == "local":
                if not os.path.exists(request.path):
                    raise ValueError(f"Path not found: {request.path}")
                
                scan_path = request.path
                stats, complexities = ScannerService._scan_directory(request.path)
            
            else:
                # GitHub Cloning
                import shutil
                import tempfile
                import subprocess
                
                # Basic URL validation
                if not request.path.startswith(("http://", "https://")):
                    raise ValueError("Invalid GitHub URL")

                with tempfile.TemporaryDirectory() as temp_dir:
                    # Clone depth 1 for speed
                    try:
                        proc = await asyncio.create_subprocess_exec(
                            "git", "clone", "--depth", "1", request.path, temp_dir,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        stdout, stderr = await proc.communicate()
                        
                        if proc.returncode != 0:
                            raise ValueError(f"Failed to clone repository: {stderr.decode().strip()}")
                            
                    except FileNotFoundError:
                        raise ValueError("Git not installed on server")
                    
                    scan_path = temp_dir
                    stats, complexities = ScannerService._scan_directory(temp_dir)
                    
                    # Build graph INSIDE tempdir context (before cleanup)
                    SCANS[scan_id].stats = stats
                    SCANS[scan_id].status = ScanStatus.completed
                    ScannerService._generate_health(scan_id, stats, complexities)
                    await ScannerService._build_graph(scan_id, temp_dir)
                    return  # Skip the post-block code
            
            SCANS[scan_id].stats = stats
            SCANS[scan_id].status = ScanStatus.completed
            
            # Generate Health Data using real stats
            ScannerService._generate_health(scan_id, stats, complexities)
            
            # Trigger AST graph build for local repos
            if scan_path:
                asyncio.create_task(ScannerService._build_graph(scan_id, scan_path))
            
        except Exception as e:
            SCANS[scan_id].status = ScanStatus.failed
            SCANS[scan_id].error = str(e)

    @staticmethod
    async def _build_graph(scan_id: str, path: str):
        """Run AST graph analysis with its own DB session."""
        try:
            from app.utils.db import AsyncSessionLocal
            from app.services.graph_service import GraphService
            async with AsyncSessionLocal() as session:
                await GraphService.build_graph(scan_id, path, session)
                logger.info(f"[{scan_id}] Graph build complete")
        except Exception as e:
            logger.error(f"[{scan_id}] Graph build failed: {e}")

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
        
        HEALTH_DATA[scan_id] = RepoHealth(
            repoId=scan_id,
            riskScore=risk_score,
            circularDependencies=0, # Use dedicated tool for this normally
            complexityScore=int(avg_complexity),
            hotspots=hotspots
        )

    @staticmethod
    def get_status(scan_id: str) -> ScanResult:
        if scan_id not in SCANS:
            raise KeyError("Scan ID not found")
        return SCANS[scan_id]

    @staticmethod
    def get_health(repo_id: str) -> RepoHealth:
        if repo_id not in HEALTH_DATA:
            raise KeyError("Health data not found")
        return HEALTH_DATA[repo_id]
