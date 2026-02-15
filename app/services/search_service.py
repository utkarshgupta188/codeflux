"""
Code Search Service - Full-text search across repository files.
"""

import os
import re
import logging
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.graph import Repository, GraphFile, Symbol
from app.models.version import RepoVersion
from app.services.scanner import ScannerService

logger = logging.getLogger("search_service")


class SearchResult:
    def __init__(self, file: str, line: int, content: str, symbol: Optional[str] = None, symbol_type: Optional[str] = None):
        self.file = file
        self.line = line
        self.content = content
        self.symbol = symbol
        self.symbol_type = symbol_type


class CodeSearchResponse:
    def __init__(self, results: List[SearchResult], total_matches: int, truncated: bool):
        self.results = results
        self.total_matches = total_matches
        self.truncated = truncated


class SearchService:
    @staticmethod
    async def search(
        scan_id: str,
        query: str,
        file_type: Optional[str],
        symbol_type: Optional[str],
        case_sensitive: bool,
        regex: bool,
        limit: int,
        db: AsyncSession,
    ) -> CodeSearchResponse:
        """
        Search through repository files for the given query.
        """
        # Get repository path
        if scan_id not in ScannerService.SCANS:
            raise ValueError("Scan not found")

        scan = ScannerService.SCANS[scan_id]
        if not scan.rootPath:
            raise ValueError("Repository path not available")

        root_path = scan.rootPath

        # Load symbols from DB for context
        version_result = await db.execute(
            select(RepoVersion).where(RepoVersion.scan_id == scan_id)
        )
        version = version_result.scalar_one_or_none()

        symbol_map = {}  # file_path -> [(symbol_name, symbol_type, start_line, end_line)]

        if version:
            files_result = await db.execute(
                select(GraphFile).where(GraphFile.version_id == version.id)
            )
            files = files_result.scalars().all()

            for file in files:
                symbols_result = await db.execute(
                    select(Symbol).where(Symbol.file_id == file.id)
                )
                symbols = symbols_result.scalars().all()

                symbol_map[file.path] = [
                    (s.name, str(s.type.value if hasattr(s.type, 'value') else s.type), s.start_line, s.end_line)
                    for s in symbols
                ]

        # Prepare search pattern
        if regex:
            try:
                pattern = re.compile(query, 0 if case_sensitive else re.IGNORECASE)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}")
        else:
            if not case_sensitive:
                query = query.lower()

        # Search through files
        results = []
        total_matches = 0

        # File type extensions
        file_extensions = {
            'python': ['.py'],
            'javascript': ['.js', '.jsx'],
            'typescript': ['.ts', '.tsx'],
            'java': ['.java'],
            'go': ['.go'],
            'rust': ['.rs'],
            'cpp': ['.cpp', '.cc', '.cxx', '.h', '.hpp'],
            'c': ['.c', '.h'],
        }

        allowed_extensions = file_extensions.get(file_type.lower(), []) if file_type else None

        for root, dirs, files in os.walk(root_path):
            # Skip common ignore directories
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', 'venv', '.venv', 'dist', 'build']]

            for filename in files:
                # Filter by file type
                if allowed_extensions and not any(filename.endswith(ext) for ext in allowed_extensions):
                    continue

                # Only search code files
                if not any(filename.endswith(ext) for ext in ['.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.go', '.rs', '.cpp', '.c', '.h', '.hpp', '.cc', '.cxx']):
                    continue

                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, root_path).replace('\\', '/')

                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()

                    for line_num, line_content in enumerate(lines, start=1):
                        # Check if line matches query
                        match = False
                        if regex:
                            match = pattern.search(line_content) is not None
                        else:
                            search_content = line_content if case_sensitive else line_content.lower()
                            match = query in search_content

                        if match:
                            total_matches += 1

                            # Find which symbol this line belongs to
                            symbol_name = None
                            sym_type = None

                            if rel_path in symbol_map:
                                for sym_name, sym_t, start, end in symbol_map[rel_path]:
                                    if start <= line_num <= end:
                                        # Filter by symbol type if specified
                                        if symbol_type and sym_t.lower() != symbol_type.lower():
                                            continue
                                        symbol_name = sym_name
                                        sym_type = sym_t
                                        break

                            # Skip if symbol type filter doesn't match
                            if symbol_type and not sym_type:
                                continue

                            if len(results) < limit:
                                results.append(SearchResult(
                                    file=rel_path,
                                    line=line_num,
                                    content=line_content.strip(),
                                    symbol=symbol_name,
                                    symbol_type=sym_type,
                                ))

                            if len(results) >= limit:
                                break

                    if len(results) >= limit:
                        break

                except Exception as e:
                    logger.warning(f"Failed to search file {file_path}: {e}")
                    continue

            if len(results) >= limit:
                break

        return CodeSearchResponse(
            results=results,
            total_matches=total_matches,
            truncated=total_matches > limit,
        )
