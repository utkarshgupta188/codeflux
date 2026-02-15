"""
Diff Service - Compare two repository scans to show changes.
"""

import logging
from typing import Dict, Set, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.graph import GraphFile, Symbol
from app.models.version import RepoVersion

logger = logging.getLogger("diff_service")


class FileDiff:
    def __init__(self, file: str, status: str, symbols_added: int, symbols_removed: int, symbols_modified: int):
        self.file = file
        self.status = status
        self.symbols_added = symbols_added
        self.symbols_removed = symbols_removed
        self.symbols_modified = symbols_modified


class DiffResponse:
    def __init__(self, base_scan_id: str, head_scan_id: str, files_changed: List[FileDiff],
                 total_files_added: int, total_files_removed: int, total_files_modified: int, symbols_changed: int):
        self.base_scan_id = base_scan_id
        self.head_scan_id = head_scan_id
        self.files_changed = files_changed
        self.total_files_added = total_files_added
        self.total_files_removed = total_files_removed
        self.total_files_modified = total_files_modified
        self.symbols_changed = symbols_changed


class DiffService:
    @staticmethod
    async def compare(
        base_scan_id: str,
        head_scan_id: str,
        db: AsyncSession,
    ) -> DiffResponse:
        """
        Compare two scans and return the differences.
        """
        # Load base version
        base_version_result = await db.execute(
            select(RepoVersion).where(RepoVersion.scan_id == base_scan_id)
        )
        base_version = base_version_result.scalar_one_or_none()
        if not base_version:
            raise ValueError(f"Base scan not found: {base_scan_id}")

        # Load head version
        head_version_result = await db.execute(
            select(RepoVersion).where(RepoVersion.scan_id == head_scan_id)
        )
        head_version = head_version_result.scalar_one_or_none()
        if not head_version:
            raise ValueError(f"Head scan not found: {head_scan_id}")

        # Load files for base version
        base_files_result = await db.execute(
            select(GraphFile).where(GraphFile.version_id == base_version.id)
        )
        base_files = base_files_result.scalars().all()
        base_file_map: Dict[str, GraphFile] = {f.path: f for f in base_files}

        # Load files for head version
        head_files_result = await db.execute(
            select(GraphFile).where(GraphFile.version_id == head_version.id)
        )
        head_files = head_files_result.scalars().all()
        head_file_map: Dict[str, GraphFile] = {f.path: f for f in head_files}

        # Compare files
        base_paths = set(base_file_map.keys())
        head_paths = set(head_file_map.keys())

        added_files = head_paths - base_paths
        removed_files = base_paths - head_paths
        common_files = base_paths & head_paths

        files_changed: List[FileDiff] = []
        total_symbols_changed = 0

        # Added files
        for path in added_files:
            head_file = head_file_map[path]
            symbols_result = await db.execute(
                select(Symbol).where(Symbol.file_id == head_file.id)
            )
            symbols = symbols_result.scalars().all()
            symbol_count = len(symbols)
            total_symbols_changed += symbol_count

            files_changed.append(FileDiff(
                file=path,
                status="added",
                symbols_added=symbol_count,
                symbols_removed=0,
                symbols_modified=0,
            ))

        # Removed files
        for path in removed_files:
            base_file = base_file_map[path]
            symbols_result = await db.execute(
                select(Symbol).where(Symbol.file_id == base_file.id)
            )
            symbols = symbols_result.scalars().all()
            symbol_count = len(symbols)
            total_symbols_changed += symbol_count

            files_changed.append(FileDiff(
                file=path,
                status="removed",
                symbols_added=0,
                symbols_removed=symbol_count,
                symbols_modified=0,
            ))

        # Modified files (compare symbols)
        for path in common_files:
            base_file = base_file_map[path]
            head_file = head_file_map[path]

            # Load symbols for base
            base_symbols_result = await db.execute(
                select(Symbol).where(Symbol.file_id == base_file.id)
            )
            base_symbols = base_symbols_result.scalars().all()
            base_symbol_names = {s.qualified_name or s.name for s in base_symbols}

            # Load symbols for head
            head_symbols_result = await db.execute(
                select(Symbol).where(Symbol.file_id == head_file.id)
            )
            head_symbols = head_symbols_result.scalars().all()
            head_symbol_names = {s.qualified_name or s.name for s in head_symbols}

            # Compare symbols
            added_symbols = head_symbol_names - base_symbol_names
            removed_symbols = base_symbol_names - head_symbol_names
            common_symbols = base_symbol_names & head_symbol_names

            # Check for modifications in common symbols (line number changes)
            modified_symbols = 0
            base_symbol_map = {(s.qualified_name or s.name): s for s in base_symbols}
            head_symbol_map = {(s.qualified_name or s.name): s for s in head_symbols}

            for sym_name in common_symbols:
                base_sym = base_symbol_map[sym_name]
                head_sym = head_symbol_map[sym_name]
                if base_sym.start_line != head_sym.start_line or base_sym.end_line != head_sym.end_line:
                    modified_symbols += 1

            # Only include if there are changes
            if added_symbols or removed_symbols or modified_symbols:
                total_symbols_changed += len(added_symbols) + len(removed_symbols) + modified_symbols

                files_changed.append(FileDiff(
                    file=path,
                    status="modified",
                    symbols_added=len(added_symbols),
                    symbols_removed=len(removed_symbols),
                    symbols_modified=modified_symbols,
                ))

        # Sort by status (removed, modified, added) then by file name
        status_order = {"removed": 0, "modified": 1, "added": 2}
        files_changed.sort(key=lambda f: (status_order[f.status], f.file))

        return DiffResponse(
            base_scan_id=base_scan_id,
            head_scan_id=head_scan_id,
            files_changed=files_changed,
            total_files_added=len(added_files),
            total_files_removed=len(removed_files),
            total_files_modified=len([f for f in files_changed if f.status == "modified"]),
            symbols_changed=total_symbols_changed,
        )

