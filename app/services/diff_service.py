import logging
from typing import Dict, List, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.version import RepoVersion
from app.models.graph import GraphFile, Symbol, Edge

logger = logging.getLogger("diff.service")

class DiffService:
    @staticmethod
    async def compare_versions(
        base_version_id: str,
        head_version_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Compare two graph snapshots.
        """
        # Load both versions
        base = await DiffService._load_full_graph(base_version_id, db)
        head = await DiffService._load_full_graph(head_version_id, db)
        
        # 1. File Diff
        base_files = {f.path for f in base["files"]}
        head_files = {f.path for f in head["files"]}
        
        added_files = list(head_files - base_files)
        removed_files = list(base_files - head_files)
        
        # 2. Complexity & Risk Delta
        # We need to sum up complexity from files (using the data we just loaded)
        # Note: We didn't store complexity directly on GraphFile in the DB schema provided in context, 
        # but the Scanner calculates it. 
        # Actually scanner *returns* complexity list, but GraphService doesn't *persist* it to GraphFile provided in context.
        # Wait, the prompt requirements said: "Complexity delta".
        # Check GraphFile model again... 
        # It has `path` and `module_name`. 
        # `RepoVersion` has `complexity_score` and `risk_score` columns I added.
        # So I can just compare the aggregates.
        
        base_ver = await db.get(RepoVersion, base_version_id)
        head_ver = await db.get(RepoVersion, head_version_id)
        
        complexity_delta = (head_ver.complexity_score or 0) - (base_ver.complexity_score or 0)
        risk_delta = (head_ver.risk_score or 0) - (base_ver.risk_score or 0)

        # 3. Dependency Changes
        # This is harder. Map edges by (source_path.symbol, target_path.symbol)
        # For now, let's just return edge count delta as a proxy, 
        # or list specifically added/removed edges if feasible.
        # Given "dependency_changes" requirement, let's try to identify new edges.
        
        base_edges = DiffService._map_edges(base)
        head_edges = DiffService._map_edges(head)
        
        added_edges = []
        for key, desc in head_edges.items():
            if key not in base_edges:
                added_edges.append(f"Added: {desc}")
                
        removed_edges = []
        for key, desc in base_edges.items():
            if key not in head_edges:
                removed_edges.append(f"Removed: {desc}")

        return {
            "added_files": added_files,
            "removed_files": removed_files,
            "dependency_changes": added_edges + removed_edges,
            "complexity_delta": complexity_delta,
            "risk_delta": risk_delta,
            "circular_dependency_delta": 0 # Placeholder for now
        }

    @staticmethod
    async def _load_full_graph(version_id: str, db: AsyncSession):
        # Fetch files
        files_res = await db.execute(select(GraphFile).where(GraphFile.version_id == version_id))
        files = files_res.scalars().all()
        file_ids = [f.id for f in files]
        file_map = {f.id: f for f in files}

        if not file_ids:
            return {"files": [], "symbols": [], "edges": []}

        # Fetch symbols
        sym_res = await db.execute(select(Symbol).where(Symbol.file_id.in_(file_ids)))
        symbols = sym_res.scalars().all()
        sym_ids = [s.id for s in symbols]
        sym_map = {s.id: s for s in symbols}

        # Fetch edges
        if not sym_ids:
             return {"files": files, "symbols": [], "edges": []}

        edge_res = await db.execute(select(Edge).where(Edge.source_id.in_(sym_ids)))
        edges = edge_res.scalars().all()

        return {"files": files, "symbols": symbols, "edges": edges, "file_map": file_map, "sym_map": sym_map}

    @staticmethod
    def _map_edges(graph_data):
        """Map edge to a unique signature: source_file:sym -> target_file:sym"""
        sig_map = {}
        files = graph_data["file_map"]
        syms = graph_data["sym_map"]
        
        for e in graph_data["edges"]:
            if e.source_id not in syms or e.target_id not in syms:
                continue
                
            src = syms[e.source_id]
            tgt = syms[e.target_id]
            
            src_file = files.get(src.file_id)
            tgt_file = files.get(tgt.file_id)
            
            if not src_file or not tgt_file:
                continue
                
            # Signature: "file.py::func -> other.py::class"
            key = (src_file.path, src.name, tgt_file.path, tgt.name, str(e.relation))
            desc = f"{src_file.path}::{src.name} --[{e.relation}]--> {tgt_file.path}::{tgt.name}"
            sig_map[key] = desc
            
        return sig_map
