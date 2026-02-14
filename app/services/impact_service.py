"""
Impact Simulation Service — deterministic change impact analysis via graph traversal.

Given a file or symbol, performs bounded BFS on the structural graph to compute:
  - Affected files and symbols (transitive dependents)
  - Impact score (weighted by depth and edge type)
  - Risk delta (change in circular dependency exposure)
  - Maximum dependency depth reached

No LLM. Purely algorithmic. Deterministic output for same graph state.
"""

import logging
from typing import List, Dict, Set, Optional, Any
from dataclasses import dataclass, field
from collections import deque

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.graph import Repository, GraphFile, Symbol, Edge, EdgeRelation
from app.services.graph_service import GraphService

logger = logging.getLogger("impact_service")

# ─── Edge weights for impact scoring ────────────────────

EDGE_WEIGHTS: Dict[str, float] = {
    "calls":   1.0,    # direct call dependency — highest impact
    "imports": 0.8,    # module-level dependency
    "defines": 0.3,    # structural containment — lower impact
}

DEPTH_DECAY = 0.7  # Impact decays by 30% per hop


# ─── Result types ───────────────────────────────────────

@dataclass
class AffectedSymbol:
    name: str
    qualified_name: str
    type: str
    file: str
    depth: int

@dataclass
class ImpactResult:
    affected_files: List[str] = field(default_factory=list)
    affected_symbols: List[Dict[str, Any]] = field(default_factory=list)
    impact_score: float = 0.0
    risk_increase: float = 0.0
    max_depth: int = 0
    total_affected: int = 0
    circular_risk: bool = False


class ImpactService:
    """
    BFS-based change impact simulation on the persisted structural graph.
    All queries are against the DB — no in-memory graph required.
    """

    @staticmethod
    async def simulate(
        scan_id: str,
        file: Optional[str],
        symbol: Optional[str],
        max_depth: int,
        db: AsyncSession,
    ) -> ImpactResult:
        """
        Entry point. Loads the graph, finds seed node(s), runs BFS,
        computes impact score and risk delta. Deterministic.
        """
        result = ImpactResult()

        # ── 1. Load graph entities ──────────────────────
        repo_row = await db.execute(
            select(Repository).where(Repository.scan_id == scan_id)
        )
        repo = repo_row.scalar_one_or_none()
        if not repo:
            return result

        files_result = await db.execute(
            select(GraphFile).where(GraphFile.repo_id == repo.id)
        )
        files = files_result.scalars().all()
        file_path_map = {f.id: f.path for f in files}
        path_to_file = {f.path: f for f in files}

        all_file_ids = {f.id for f in files}
        symbols_result = await db.execute(
            select(Symbol).where(Symbol.file_id.in_(all_file_ids))
        )
        symbols = symbols_result.scalars().all()

        sym_by_id: Dict[str, Symbol] = {s.id: s for s in symbols}
        sym_by_qname: Dict[str, Symbol] = {}
        sym_by_name: Dict[str, List[Symbol]] = {}
        for s in symbols:
            if s.qualified_name:
                sym_by_qname[s.qualified_name] = s
            sym_by_name.setdefault(s.name, []).append(s)

        symbol_ids = {s.id for s in symbols}
        edges_result = await db.execute(
            select(Edge).where(
                Edge.source_id.in_(symbol_ids) | Edge.target_id.in_(symbol_ids)
            )
        )
        edges = edges_result.scalars().all()

        # ── 2. Build adjacency (forward + reverse) ─────
        # forward: source → [(target, relation)]
        # reverse: target → [(source, relation)]
        forward: Dict[str, List[tuple]] = {}
        reverse: Dict[str, List[tuple]] = {}
        for e in edges:
            rel = e.relation.value if hasattr(e.relation, 'value') else str(e.relation)
            forward.setdefault(e.source_id, []).append((e.target_id, rel))
            reverse.setdefault(e.target_id, []).append((e.source_id, rel))

        # ── 3. Find seed nodes ─────────────────────────
        seed_ids: Set[str] = set()

        if symbol:
            # Try qualified name first, then plain name
            if symbol in sym_by_qname:
                seed_ids.add(sym_by_qname[symbol].id)
            elif symbol in sym_by_name:
                for s in sym_by_name[symbol]:
                    seed_ids.add(s.id)
            else:
                # Fuzzy: partial match
                for qname, s in sym_by_qname.items():
                    if symbol in qname or qname.endswith(symbol):
                        seed_ids.add(s.id)
                        break

        if file:
            # Find all symbols in this file
            norm = file.replace("\\", "/")
            for f_obj in files:
                f_path = f_obj.path.replace("\\", "/")
                if f_path == norm or f_path.endswith(norm) or norm.endswith(f_path):
                    for s in symbols:
                        if s.file_id == f_obj.id:
                            seed_ids.add(s.id)
                    break

        if not seed_ids:
            return result

        # ── 4. BFS traversal (both directions) ─────────
        visited: Set[str] = set()
        depth_map: Dict[str, int] = {}  # symbol_id → depth
        impact_sum = 0.0

        queue: deque = deque()
        for sid in seed_ids:
            queue.append((sid, 0))
            visited.add(sid)
            depth_map[sid] = 0

        while queue:
            current_id, depth = queue.popleft()

            if depth >= max_depth:
                continue

            # Forward edges: things this symbol affects
            for target_id, rel in forward.get(current_id, []):
                if target_id not in visited and target_id in sym_by_id:
                    visited.add(target_id)
                    next_depth = depth + 1
                    depth_map[target_id] = next_depth
                    queue.append((target_id, next_depth))

                    weight = EDGE_WEIGHTS.get(rel, 0.5)
                    impact_sum += weight * (DEPTH_DECAY ** depth)

            # Reverse edges: things that depend on this symbol
            for source_id, rel in reverse.get(current_id, []):
                if source_id not in visited and source_id in sym_by_id:
                    visited.add(source_id)
                    next_depth = depth + 1
                    depth_map[source_id] = next_depth
                    queue.append((source_id, next_depth))

                    weight = EDGE_WEIGHTS.get(rel, 0.5)
                    impact_sum += weight * (DEPTH_DECAY ** depth)

        # ── 5. Collect affected (exclude seeds) ────────
        affected_ids = visited - seed_ids
        affected_files_set: Set[str] = set()
        affected_syms: List[Dict[str, Any]] = []

        for sid in affected_ids:
            sym = sym_by_id.get(sid)
            if not sym:
                continue
            fpath = file_path_map.get(sym.file_id, "unknown")
            affected_files_set.add(fpath)
            sym_type = sym.type.value if hasattr(sym.type, 'value') else str(sym.type)
            if sym_type != "import":  # skip raw imports for cleanliness
                affected_syms.append({
                    "name": sym.name,
                    "qualified_name": sym.qualified_name or sym.name,
                    "type": sym_type,
                    "file": fpath,
                    "depth": depth_map.get(sid, 0),
                })

        # Sort by depth, then name
        affected_syms.sort(key=lambda x: (x["depth"], x["name"]))

        # ── 6. Risk delta: circular dependency check ───
        # Check if any affected symbol is part of a cycle
        graph_response = await GraphService.get_graph(scan_id, db)
        cycle_names: Set[str] = set()
        for c in graph_response.circular_dependencies:
            for name in c.cycle:
                cycle_names.add(name)

        circular_risk = False
        cycle_affected = 0
        for sym_info in affected_syms:
            qn = sym_info.get("qualified_name", "")
            if qn in cycle_names or sym_info.get("name", "") in cycle_names:
                circular_risk = True
                cycle_affected += 1

        risk_increase = 0.0
        if circular_risk:
            risk_increase = min(25.0, cycle_affected * 5.0)

        # Also factor in breadth of impact
        file_ratio = len(affected_files_set) / max(len(files), 1)
        risk_increase += file_ratio * 15.0  # up to 15 points for wide blast radius

        # ── 7. Build result ────────────────────────────
        result.affected_files = sorted(affected_files_set)
        result.affected_symbols = affected_syms
        result.impact_score = round(impact_sum, 2)
        result.risk_increase = round(risk_increase, 2)
        result.max_depth = max(depth_map.values()) if depth_map else 0
        result.total_affected = len(affected_syms)
        result.circular_risk = circular_risk

        return result
