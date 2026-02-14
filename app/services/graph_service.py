"""
Graph Service — orchestrates AST parsing, DB persistence, and cycle detection.

Public interface:
    GraphService.build_graph(scan_id, repo_path, db)   → persists graph
    GraphService.get_graph(scan_id, db)                → returns GraphResponse
"""

import asyncio
import logging
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.graph import (
    Repository, GraphFile, Symbol, Edge,
    SymbolType, EdgeRelation, _uuid,
)
from app.models.graph_schemas import (
    SymbolNode, GraphEdge, CyclePath, GraphResponse,
)
from app.services.ast_visitor import parse_file, FileAnalysis

logger = logging.getLogger("graph.service")

# Directories to skip during file walk
SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", "venv", ".venv",
    "env", ".env", "dist", "build", ".mypy_cache", ".pytest_cache",
    ".tox", "eggs", "*.egg-info",
}


class GraphService:
    """Static methods — no instance state. All IO is async."""

    # ── Public ───────────────────────────────────────

    @staticmethod
    async def build_graph(scan_id: str, repo_path: str, db: AsyncSession) -> None:
        """
        Full pipeline: walk → parse → resolve → persist → detect cycles.
        Runs heavy file I/O in a thread pool.
        """
        root = Path(repo_path)

        # 1. Collect .py files (sync, but fast)
        py_files = await asyncio.to_thread(GraphService._walk_python_files, root)
        logger.info(f"[{scan_id}] Found {len(py_files)} Python files")

        if not py_files:
            logger.warning(f"[{scan_id}] No Python files found in {repo_path}")
            return

        # 2. Parse all files (CPU-bound, run in thread)
        analyses = await asyncio.to_thread(GraphService._parse_all, py_files, root)
        logger.info(f"[{scan_id}] Parsed {len(analyses)} files successfully")

        # 3. Build DB entities
        repo_id = _uuid()
        repo = Repository(id=repo_id, scan_id=scan_id, root_path=str(root))

        file_records: List[GraphFile] = []
        symbol_records: List[Symbol] = []
        edge_records: List[Edge] = []

        # Maps for edge resolution
        symbol_id_by_qname: Dict[str, str] = {}
        module_symbol_ids: Dict[str, str] = {}   # module_name → symbol_id

        for analysis in analyses:
            file_id = _uuid()
            file_rec = GraphFile(
                id=file_id,
                repo_id=repo_id,
                path=analysis.relative_path,
                module_name=analysis.module_name,
            )
            file_records.append(file_rec)

            for sym_info in analysis.symbols:
                sym_id = _uuid()
                sym_type = GraphService._map_symbol_type(sym_info.type)
                sym = Symbol(
                    id=sym_id,
                    name=sym_info.name,
                    qualified_name=sym_info.qualified_name,
                    type=sym_type,
                    file_id=file_id,
                    start_line=sym_info.start_line,
                    end_line=sym_info.end_line,
                )
                symbol_records.append(sym)
                symbol_id_by_qname[sym_info.qualified_name] = sym_id

                if sym_info.type == "module":
                    module_symbol_ids[analysis.module_name] = sym_id

        # 4. Resolve edges
        # 4a. defines: module → class/function
        for analysis in analyses:
            module_qname = analysis.module_name
            module_sid = symbol_id_by_qname.get(module_qname)
            if not module_sid:
                continue

            for sym_info in analysis.symbols:
                if sym_info.type in ("class", "function") and "." not in sym_info.name:
                    target_sid = symbol_id_by_qname.get(sym_info.qualified_name)
                    if target_sid and target_sid != module_sid:
                        edge_records.append(Edge(
                            id=_uuid(),
                            source_id=module_sid,
                            target_id=target_sid,
                            relation=EdgeRelation.defines,
                        ))

        # 4b. imports: file's module symbol → imported module symbol
        for analysis in analyses:
            module_sid = symbol_id_by_qname.get(analysis.module_name)
            if not module_sid:
                continue

            for imp in analysis.imports:
                target_module = imp.module
                # Try exact match, then partial
                target_sid = module_symbol_ids.get(target_module)
                if not target_sid:
                    # Try matching by suffix (e.g. "app.config" matches repo's "app.config")
                    for mname, sid in module_symbol_ids.items():
                        if mname.endswith(target_module) or target_module.endswith(mname):
                            target_sid = sid
                            break

                if target_sid and target_sid != module_sid:
                    edge_records.append(Edge(
                        id=_uuid(),
                        source_id=module_sid,
                        target_id=target_sid,
                        relation=EdgeRelation.imports,
                    ))

        # 4c. calls: caller symbol → callee symbol (best-effort name match)
        for analysis in analyses:
            for call in analysis.calls:
                caller_sid = symbol_id_by_qname.get(
                    f"{analysis.module_name}.{call.caller_qualified_name}"
                    if call.caller_qualified_name != "<module>"
                    else analysis.module_name
                )
                if not caller_sid:
                    continue

                # Try to resolve callee
                callee_sid = GraphService._resolve_callee(
                    call.callee_name, analysis.module_name, symbol_id_by_qname
                )
                if callee_sid and callee_sid != caller_sid:
                    edge_records.append(Edge(
                        id=_uuid(),
                        source_id=caller_sid,
                        target_id=callee_sid,
                        relation=EdgeRelation.calls,
                    ))

        # 5. Persist — single transaction, bulk insert
        # Clear previous graph for this scan_id first
        existing = await db.execute(
            select(Repository).where(Repository.scan_id == scan_id)
        )
        old_repo = existing.scalar_one_or_none()
        if old_repo:
            await db.delete(old_repo)
            await db.flush()

        db.add(repo)
        db.add_all(file_records)
        db.add_all(symbol_records)
        db.add_all(edge_records)
        await db.commit()

        logger.info(
            f"[{scan_id}] Graph persisted: "
            f"{len(file_records)} files, {len(symbol_records)} symbols, {len(edge_records)} edges"
        )

    @staticmethod
    async def get_graph(scan_id: str, db: AsyncSession) -> GraphResponse:
        """Query the persisted graph and return serialized response."""
        # Find repo
        result = await db.execute(
            select(Repository).where(Repository.scan_id == scan_id)
        )
        repo = result.scalar_one_or_none()
        if not repo:
            return GraphResponse(
                scan_id=scan_id,
                total_files=0,
                total_symbols=0,
                total_edges=0,
                nodes=[],
                edges=[],
                circular_dependencies=[],
            )

        # Load files
        files_result = await db.execute(
            select(GraphFile).where(GraphFile.repo_id == repo.id)
        )
        files = files_result.scalars().all()
        file_path_map = {f.id: f.path for f in files}

        # Load symbols
        symbols_result = await db.execute(
            select(Symbol).where(Symbol.file_id.in_([f.id for f in files]))
        )
        symbols = symbols_result.scalars().all()

        # Load edges
        symbol_ids = {s.id for s in symbols}
        edges_result = await db.execute(
            select(Edge).where(Edge.source_id.in_(symbol_ids))
        )
        edges = edges_result.scalars().all()

        # Serialize nodes
        nodes = [
            SymbolNode(
                id=s.id,
                name=s.name,
                qualified_name=s.qualified_name,
                type=s.type.value if hasattr(s.type, 'value') else str(s.type),
                file=file_path_map.get(s.file_id, "unknown"),
                start_line=s.start_line,
                end_line=s.end_line,
            )
            for s in symbols
        ]

        # Serialize edges
        graph_edges = [
            GraphEdge(
                source_id=e.source_id,
                target_id=e.target_id,
                relation=e.relation.value if hasattr(e.relation, 'value') else str(e.relation),
            )
            for e in edges
            if e.target_id in symbol_ids  # Only include edges with valid targets
        ]

        # Detect cycles
        cycles = GraphService._detect_cycles(edges, symbols, file_path_map)

        return GraphResponse(
            scan_id=scan_id,
            total_files=len(files),
            total_symbols=len(symbols),
            total_edges=len(graph_edges),
            nodes=nodes,
            edges=graph_edges,
            circular_dependencies=cycles,
        )

    # ── Private ──────────────────────────────────────

    @staticmethod
    def _walk_python_files(root: Path) -> List[Path]:
        """Collect all .py files, skipping ignored directories."""
        py_files = []
        for dirpath, dirnames, filenames in os.walk(root):
            # Prune ignored dirs in-place
            dirnames[:] = [
                d for d in dirnames
                if d not in SKIP_DIRS and not d.endswith(".egg-info")
            ]
            for fname in filenames:
                if fname.endswith(".py"):
                    py_files.append(Path(dirpath) / fname)
        return py_files

    @staticmethod
    def _parse_all(files: List[Path], root: Path) -> List[FileAnalysis]:
        """Parse all files, skipping failures."""
        results = []
        for fp in files:
            analysis = parse_file(fp, root)
            if analysis:
                results.append(analysis)
        return results

    @staticmethod
    def _map_symbol_type(type_str: str) -> SymbolType:
        mapping = {
            "module": SymbolType.module,
            "class": SymbolType.class_,
            "function": SymbolType.function,
            "method": SymbolType.method,
            "import": SymbolType.import_,
        }
        return mapping.get(type_str, SymbolType.function)

    @staticmethod
    def _resolve_callee(
        callee_name: str,
        caller_module: str,
        qname_map: Dict[str, str],
    ) -> str | None:
        """Best-effort resolution of a call target to a known symbol ID."""
        # 1. Try the raw callee name in the same module
        local_qname = f"{caller_module}.{callee_name}"
        if local_qname in qname_map:
            return qname_map[local_qname]

        # 2. Try as a global qualified name
        if callee_name in qname_map:
            return qname_map[callee_name]

        # 3. Try suffix match (handles "self.method_name" → "Class.method_name")
        #    Also handles "module.func" patterns
        parts = callee_name.split(".")
        if len(parts) >= 2:
            # Try last two parts
            suffix = ".".join(parts[-2:])
            for qname, sid in qname_map.items():
                if qname.endswith(suffix):
                    return sid

            # Try just the last part (method name)
            last = parts[-1]
            for qname, sid in qname_map.items():
                if qname.endswith(f".{last}"):
                    return sid

        return None

    @staticmethod
    def _detect_cycles(
        edges: list,
        symbols: list,
        file_map: Dict[str, str],
    ) -> List[CyclePath]:
        """
        DFS-based cycle detection on both import and call edges.
        Uses 3-color marking: WHITE (unvisited), GRAY (in-stack), BLACK (done).
        """
        cycles: List[CyclePath] = []

        for relation_type in ("imports", "calls"):
            # Build adjacency list for this relation type
            adj: Dict[str, List[str]] = defaultdict(list)
            filtered = [
                e for e in edges
                if (e.relation.value if hasattr(e.relation, 'value') else str(e.relation)) == relation_type
            ]

            for e in filtered:
                adj[e.source_id].append(e.target_id)

            # DFS
            WHITE, GRAY, BLACK = 0, 1, 2
            color: Dict[str, int] = defaultdict(int)  # defaults to WHITE=0
            parent: Dict[str, str | None] = {}

            # Symbol name lookup
            sym_name = {s.id: (s.qualified_name or s.name) for s in symbols}

            def dfs(u: str, path: List[str]) -> None:
                color[u] = GRAY
                path.append(u)

                for v in adj.get(u, []):
                    if color[v] == GRAY:
                        # Found cycle: extract from v's position in path
                        cycle_start = path.index(v)
                        cycle_ids = path[cycle_start:] + [v]
                        cycle_names = [sym_name.get(nid, nid) for nid in cycle_ids]
                        cycles.append(CyclePath(
                            cycle=cycle_names,
                            type="import" if relation_type == "imports" else "call",
                        ))
                    elif color[v] == WHITE:
                        dfs(v, path)

                path.pop()
                color[u] = BLACK

            all_nodes = set(adj.keys())
            for targets in adj.values():
                all_nodes.update(targets)

            for node in all_nodes:
                if color[node] == WHITE:
                    dfs(node, [])

        return cycles
