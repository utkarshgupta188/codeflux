"""
Context Builder — constructs structured, hallucination-resistant prompts
from repository analysis data for AI-powered code Q&A.

Design principles:
  - No raw source dumped → only structured summaries
  - Deterministic context assembly → reproducible results
  - Bounded token usage → fixed sections, capped lists
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.graph import Repository, GraphFile, Symbol, Edge, SymbolType, EdgeRelation
from app.models.graph_schemas import GraphResponse
from app.services.graph_service import GraphService
from app.services.scanner import ScannerService

logger = logging.getLogger("context_builder")


# ─── Structured context payload ─────────────────────────

@dataclass
class RepoContext:
    """Intermediate payload — everything the prompt needs, nothing it doesn't."""
    scan_id: str
    total_files: int = 0
    total_symbols: int = 0
    total_edges: int = 0

    # Health metrics
    risk_score: float = 0.0
    complexity_score: float = 0.0

    # Top hotspot files (max 8)
    hotspots: List[Dict[str, Any]] = field(default_factory=list)

    # Circular dependencies
    cycles: List[Dict[str, Any]] = field(default_factory=list)

    # Top connected symbols by edge count (max 10)
    top_symbols: List[Dict[str, Any]] = field(default_factory=list)

    # Edge distribution summary
    edge_summary: Dict[str, int] = field(default_factory=dict)

    # File → symbol type distribution
    file_summaries: List[Dict[str, Any]] = field(default_factory=list)


class ContextBuilder:
    """
    Assembles structured context from graph + health data.
    All queries are bounded to prevent token explosion.
    """

    @staticmethod
    async def build_context(scan_id: str, db: AsyncSession) -> RepoContext:
        """Build the full context payload for a scan."""
        ctx = RepoContext(scan_id=scan_id)

        # 1. Graph data (reuse existing service)
        graph = await GraphService.get_graph(scan_id, db)
        ctx.total_files = graph.total_files
        ctx.total_symbols = graph.total_symbols
        ctx.total_edges = graph.total_edges

        # 2. Health data (from in-memory scan store)
        try:
            health = ScannerService.get_health(scan_id)
            ctx.risk_score = health.riskScore
            ctx.complexity_score = health.complexityScore
            ctx.hotspots = [
                {"file": h.file, "score": h.score}
                for h in (health.hotspots or [])[:8]
            ]
        except (KeyError, Exception) as e:
            logger.warning(f"[{scan_id}] Health data unavailable: {e}")

        # 3. Circular dependencies
        ctx.cycles = [
            {"cycle": c.cycle, "type": c.type}
            for c in graph.circular_dependencies[:5]
        ]

        # 4. Edge distribution
        edge_counts: Dict[str, int] = {}
        for edge in graph.edges:
            edge_counts[edge.relation] = edge_counts.get(edge.relation, 0) + 1
        ctx.edge_summary = edge_counts

        # 5. Top connected symbols (by edge count)
        symbol_edge_count: Dict[str, int] = {}
        symbol_map: Dict[str, Any] = {}
        for node in graph.nodes:
            symbol_map[node.id] = node
            symbol_edge_count[node.id] = 0

        for edge in graph.edges:
            if edge.source_id in symbol_edge_count:
                symbol_edge_count[edge.source_id] += 1
            if edge.target_id in symbol_edge_count:
                symbol_edge_count[edge.target_id] += 1

        top_ids = sorted(symbol_edge_count, key=symbol_edge_count.get, reverse=True)[:10]
        ctx.top_symbols = [
            {
                "name": symbol_map[sid].name,
                "type": symbol_map[sid].type,
                "file": symbol_map[sid].file,
                "connections": symbol_edge_count[sid],
            }
            for sid in top_ids
            if sid in symbol_map
        ]

        # 6. Per-file symbol distribution (top 10 files by symbol count)
        file_sym_count: Dict[str, Dict[str, int]] = {}
        for node in graph.nodes:
            f = node.file
            if f not in file_sym_count:
                file_sym_count[f] = {"classes": 0, "functions": 0, "methods": 0, "imports": 0}
            t = node.type
            if t == "class":
                file_sym_count[f]["classes"] += 1
            elif t == "function":
                file_sym_count[f]["functions"] += 1
            elif t == "method":
                file_sym_count[f]["methods"] += 1
            elif t == "import":
                file_sym_count[f]["imports"] += 1

        sorted_files = sorted(file_sym_count.items(), key=lambda x: sum(x[1].values()), reverse=True)[:10]
        ctx.file_summaries = [
            {"file": f, **counts}
            for f, counts in sorted_files
        ]

        return ctx

    @staticmethod
    def build_system_prompt(ctx: RepoContext) -> str:
        """
        Construct a structured system prompt from context.
        Deterministic, bounded, no hallucination bait.
        """
        lines = [
            "You are a senior code intelligence assistant analyzing a Python repository.",
            "Answer ONLY based on the structural analysis data provided below.",
            "If the data does not contain enough information, say so explicitly.",
            "Do NOT guess file contents or fabricate code. Focus on architecture and structure.",
            "",
            "═══ REPOSITORY OVERVIEW ═══",
            f"Files: {ctx.total_files} | Symbols: {ctx.total_symbols} | Edges: {ctx.total_edges}",
            f"Risk Score: {ctx.risk_score}/100 | Complexity: {ctx.complexity_score}/100",
        ]

        # Edge distribution
        if ctx.edge_summary:
            lines.append("")
            lines.append("═══ RELATIONSHIP DISTRIBUTION ═══")
            for rel, count in ctx.edge_summary.items():
                lines.append(f"  {rel}: {count}")

        # Hotspots
        if ctx.hotspots:
            lines.append("")
            lines.append("═══ HOTSPOT FILES (highest complexity) ═══")
            for h in ctx.hotspots:
                lines.append(f"  • {h['file']} — score: {h['score']}")

        # Circular dependencies
        if ctx.cycles:
            lines.append("")
            lines.append("═══ CIRCULAR DEPENDENCIES ═══")
            for c in ctx.cycles:
                chain = " → ".join(c["cycle"])
                lines.append(f"  [{c['type']}] {chain}")
        else:
            lines.append("")
            lines.append("═══ CIRCULAR DEPENDENCIES ═══")
            lines.append("  None detected.")

        # Top connected symbols
        if ctx.top_symbols:
            lines.append("")
            lines.append("═══ MOST CONNECTED SYMBOLS ═══")
            for s in ctx.top_symbols:
                lines.append(f"  • {s['name']} ({s['type']}) in {s['file']} — {s['connections']} connections")

        # File summaries
        if ctx.file_summaries:
            lines.append("")
            lines.append("═══ FILE STRUCTURE (top files by symbol count) ═══")
            for f in ctx.file_summaries:
                parts = []
                if f.get("classes"):   parts.append(f"{f['classes']} cls")
                if f.get("functions"): parts.append(f"{f['functions']} fn")
                if f.get("methods"):   parts.append(f"{f['methods']} mtd")
                if f.get("imports"):   parts.append(f"{f['imports']} imp")
                lines.append(f"  • {f['file']}: {', '.join(parts)}")

        lines.append("")
        lines.append("═══ END OF CONTEXT ═══")
        lines.append("Answer the user's question based ONLY on the above data.")

        return "\n".join(lines)
