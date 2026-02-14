/**
 * Transforms the backend GraphResponse into React Flow nodes and edges.
 * Supports two view modes:
 *   - file:   Shows only module-level nodes with import edges
 *   - symbol: Shows all symbols with all edge types
 */

import type { Node, Edge } from '@xyflow/react';
import type { GraphResponse, SymbolNode, ViewMode } from '../types';

// ─── Color palette ──────────────────────────────────────

const NODE_COLORS: Record<string, string> = {
    module: '#3b82f6',  // blue
    class: '#8b5cf6',  // purple
    function: '#10b981',  // emerald
    method: '#14b8a6',  // teal
    import: '#6b7280',  // gray
};

const EDGE_COLORS: Record<string, string> = {
    defines: '#475569',
    imports: '#3b82f6',
    calls: '#f59e0b',
};

// ─── Helpers ────────────────────────────────────────────

function shortName(name: string): string {
    const parts = name.split('.');
    return parts.length > 2 ? parts.slice(-2).join('.') : name;
}

function nodeSize(type: string): { width: number; height: number } {
    if (type === 'module') return { width: 200, height: 50 };
    if (type === 'class') return { width: 170, height: 44 };
    return { width: 150, height: 38 };
}

// ─── Layout: simple grid (no external dep) ──────────────

function layoutNodes(
    symbols: SymbolNode[],
    mode: ViewMode,
): Node[] {
    // Group by file
    const byFile = new Map<string, SymbolNode[]>();
    for (const sym of symbols) {
        const list = byFile.get(sym.file) || [];
        list.push(sym);
        byFile.set(sym.file, list);
    }

    const nodes: Node[] = [];
    let fileX = 0;

    for (const [file, syms] of byFile) {
        const moduleSym = syms.find(s => s.type === 'module');
        const childSyms = syms.filter(s => s.type !== 'module' && s.type !== 'import');

        if (mode === 'file') {
            // File-level: one node per file
            const size = nodeSize('module');
            nodes.push({
                id: moduleSym?.id || file,
                type: 'graphNode',
                position: { x: fileX, y: 0 },
                data: {
                    label: shortName(file.replace('.py', '')),
                    symbolType: 'module',
                    color: NODE_COLORS.module,
                    symbol: moduleSym || { id: file, name: file, type: 'module', file, start_line: 0, end_line: 0, qualified_name: file },
                    childCount: childSyms.length,
                    ...size,
                },
            });
            fileX += size.width + 60;
        } else {
            // Symbol-level: module node + children stacked below
            const size = nodeSize('module');
            if (moduleSym) {
                nodes.push({
                    id: moduleSym.id,
                    type: 'graphNode',
                    position: { x: fileX, y: 0 },
                    data: {
                        label: shortName(moduleSym.name),
                        symbolType: 'module',
                        color: NODE_COLORS.module,
                        symbol: moduleSym,
                        childCount: childSyms.length,
                        ...size,
                    },
                });
            }

            let childY = 80;
            for (const sym of childSyms) {
                const csize = nodeSize(sym.type);
                nodes.push({
                    id: sym.id,
                    type: 'graphNode',
                    position: { x: fileX + 15, y: childY },
                    data: {
                        label: sym.name,
                        symbolType: sym.type,
                        color: NODE_COLORS[sym.type] || NODE_COLORS.function,
                        symbol: sym,
                        ...csize,
                    },
                });
                childY += csize.height + 16;
            }

            fileX += Math.max(size.width, 170) + 80;
        }
    }

    return nodes;
}

// ─── Public API ─────────────────────────────────────────

export interface TransformedGraph {
    nodes: Node[];
    edges: Edge[];
    cycleNodeIds: Set<string>;
}

export function transformGraph(
    data: GraphResponse,
    mode: ViewMode,
): TransformedGraph {
    // Collect cycle-involved node IDs
    const cycleNodeIds = new Set<string>();
    // Build a names→id map for cycle matching
    const nameToIds = new Map<string, string>();
    for (const n of data.nodes) {
        if (n.qualified_name) nameToIds.set(n.qualified_name, n.id);
        nameToIds.set(n.name, n.id);
    }
    for (const cycle of data.circular_dependencies) {
        for (const name of cycle.cycle) {
            const id = nameToIds.get(name);
            if (id) cycleNodeIds.add(id);
        }
    }

    // Filter symbols for this view mode
    let filteredSymbols = data.nodes;
    if (mode === 'file') {
        filteredSymbols = data.nodes.filter(n => n.type === 'module');
    } else {
        // Exclude raw imports for cleanliness
        filteredSymbols = data.nodes.filter(n => n.type !== 'import');
    }

    const nodeIdSet = new Set(filteredSymbols.map(n => n.id));
    const nodes = layoutNodes(filteredSymbols, mode);

    // Filter and transform edges
    const filteredEdges = data.edges.filter(e => {
        if (mode === 'file') {
            return e.relation === 'imports' && nodeIdSet.has(e.source_id) && nodeIdSet.has(e.target_id);
        }
        return nodeIdSet.has(e.source_id) && nodeIdSet.has(e.target_id);
    });

    const edges: Edge[] = filteredEdges.map((e, i) => {
        const isCycle = cycleNodeIds.has(e.source_id) && cycleNodeIds.has(e.target_id);
        return {
            id: `e-${i}`,
            source: e.source_id,
            target: e.target_id,
            type: 'smoothstep',
            animated: isCycle,
            label: e.relation,
            style: {
                stroke: isCycle ? '#ef4444' : EDGE_COLORS[e.relation] || '#475569',
                strokeWidth: isCycle ? 2.5 : 1.5,
            },
            labelStyle: {
                fill: '#9ca3af',
                fontSize: 10,
            },
        };
    });

    return { nodes, edges, cycleNodeIds };
}
