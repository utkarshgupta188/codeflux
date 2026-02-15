import os
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.services.scanner import ScannerService
from app.services.graph_service import GraphService
from app.utils.db import AsyncSessionLocal
from sqlalchemy import select
from app.models.graph import GraphFile, Symbol, Edge, EdgeRelation

# ─── Tool Definitions ──────────────────────────────────────────────

class ToolResult(BaseModel):
    output: str
    error: Optional[str] = None

class AgentTool:
    name: str = "base_tool"
    description: str = "Base tool"
    
    async def run(self, **kwargs) -> ToolResult:
        raise NotImplementedError

class ReadFileTool(AgentTool):
    name = "read_file"
    description = "Read the contents of a file. Args: path (str), start_line (int, optional), end_line (int, optional)"
    
    async def run(self, path: str, start_line: int = 1, end_line: int = -1, root_path: str = ".") -> ToolResult:
        try:
            # Path Sanitization: Strip virtual prefixes like /repo/<uuid>/
            path = re.sub(r'^/?repo/[^/]+/', '', path).lstrip('/')
            
            # Resolve absolute path properly
            full_path = os.path.join(root_path, path)
            if not os.path.exists(full_path):
                return ToolResult(output="", error=f"File not found: {path} (in {root_path})")
            
            with open(full_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            total_lines = len(lines)
            if end_line == -1:
                end_line = total_lines
            
            # Clamp
            start_line = max(1, start_line)
            end_line = min(total_lines, end_line)
            
            # Limit to 300 lines to prevent context overflow
            if end_line - start_line > 300:
                return ToolResult(output="", error=f"Range too large ({end_line - start_line} lines). Please read in chunks of 300 lines max.")
            
            content = "".join([f"{i+1}: {line}" for i, line in enumerate(lines[start_line-1:end_line], start=start_line-1)])
            return ToolResult(output=content)
        except Exception as e:
            return ToolResult(output="", error=str(e))

class SearchCodeTool(AgentTool):
    name = "search_code"
    description = "Search for a string or regex in the codebase. Args: query (str), is_regex (bool)"
    
    async def run(self, query: str, is_regex: bool = False, root_path: str = ".") -> ToolResult:
        results = []
        try:
            # Simple grep-like search
            # In a real scenario, use ripgrep or similar. Here we use python for portability in this env.
            pattern = re.compile(query) if is_regex else None
            
            count = 0
            MAX_RESULTS = 50
            
            for root, _, files in os.walk(root_path):
                if any(x in root for x in [".git", "__pycache__", "node_modules", "dist"]):
                    continue
                    
                for file in files:
                    if not file.endswith((".py", ".ts", ".tsx", ".js", ".md")):
                        continue
                        
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            lines = f.readlines()
                            
                        for i, line in enumerate(lines):
                            if (is_regex and pattern.search(line)) or (not is_regex and query in line):
                                results.append(f"{file_path}:{i+1}: {line.strip()}")
                                count += 1
                                if count >= MAX_RESULTS:
                                    break
                    except:
                        continue
                if count >= MAX_RESULTS:
                    break
            
            if not results:
                return ToolResult(output="No matches found.")
                
            return ToolResult(output="\n".join(results))
        except Exception as e:
            return ToolResult(output="", error=str(e))

class ListFilesTool(AgentTool):
    name = "list_files"
    description = "List files in a directory. Args: path (str)"
    
    async def run(self, path: str = ".", root_path: str = ".") -> ToolResult:
        try:
            # Path Sanitization: Strip virtual prefixes
            path = re.sub(r'^/?repo/[^/]+/', '', path).lstrip('/')
            if not path: path = "."
            
            full_path = os.path.join(root_path, path)
            if not os.path.exists(full_path):
                return ToolResult(output="", error=f"Path not found: {path}")
            
            files = []
            for item in os.listdir(full_path):
                if item.startswith("."): continue
                if os.path.isdir(os.path.join(full_path, item)):
                    files.append(f"[DIR] {item}")
                else:
                    files.append(f"[FILE] {item}")
            return ToolResult(output="\n".join(files))
        except Exception as e:
            return ToolResult(output="", error=str(e))

class GetHotspotsTool(AgentTool):
    name = "get_hotspots"
    description = "Get list of complex/risky files. Args: limit (int)"
    
    async def run(self, limit: int = 10, repo_id: str = None) -> ToolResult:
        # Fetch from ScannerService.HEALTH_DATA
        if not ScannerService.HEALTH_DATA:
            return ToolResult(output="No health data available. Run a scan first.")
            
        # Get specified repo or first one found
        if repo_id and repo_id in ScannerService.HEALTH_DATA:
            health = ScannerService.HEALTH_DATA[repo_id]
        else:
            repo_id = next(iter(ScannerService.HEALTH_DATA))
            health = ScannerService.HEALTH_DATA[repo_id]
        
        hotspots = sorted(health.hotspots, key=lambda x: x.score, reverse=True)[:limit]
        return ToolResult(output="\n".join([f"{h.file}: score={h.score:.1f}" for h in hotspots]))

# Register tools
TOOLS = {
    "read_file": ReadFileTool(),
    "search_code": SearchCodeTool(),
    "list_files": ListFilesTool(),
    "get_hotspots": GetHotspotsTool(),
}
