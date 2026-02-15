/**
 * GraphViewer — structural code graph visualization using React Flow.
 *
 * Features:
 *   - File-level and symbol-level view toggle
 *   - Node click → metadata panel
 *   - Circular dependency highlighting (red edges)
 *   - Dark theme integration
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import {
    ReactFlow,
    Background,
    Controls,
    MiniMap,
    useNodesState,
    useEdgesState,
    type NodeTypes,
    type Node,
    type Edge as FlowEdge,
    type NodeProps,
    Handle,
    Position,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { apiService } from '../services/repoService';
import { transformGraph } from '../utils/graphTransformer';
import type { GraphResponse, SymbolNode, ViewMode } from '../types';

// ─── Custom Node Component ─────────────────────────────

interface GraphNodeData {
    label: string;
    symbolType: string;
    color: string;
    symbol: SymbolNode;
    childCount?: number;
    width: number;
    height: number;
    [key: string]: unknown;
}

function GraphNode({ data }: NodeProps<Node<GraphNodeData>>) {
    const d = data as GraphNodeData;
    const isModule = d.symbolType === 'module';

    return (
        <>
            <Handle type="target" position={Position.Left} style={{ background: '#475569', border: 'none', width: 6, height: 6 }} />
            <div
                style={{
                    background: '#1e293b',
                    border: `1.5px solid ${d.color}`,
                    borderRadius: isModule ? 8 : 6,
                    padding: isModule ? '10px 16px' : '6px 12px',
                    minWidth: d.width,
                    cursor: 'pointer',
                    boxShadow: `0 0 12px ${d.color}20`,
                }}
            >
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <div
                        style={{
                            width: isModule ? 10 : 8,
                            height: isModule ? 10 : 8,
                            borderRadius: '50%',
                            background: d.color,
                            flexShrink: 0,
                        }}
                    />
                    <span style={{
                        color: '#e2e8f0',
                        fontSize: isModule ? 13 : 11,
                        fontWeight: isModule ? 600 : 500,
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        maxWidth: d.width - 40,
                        fontFamily: "'Inter', system-ui, sans-serif",
                    }}>
                        {d.label}
                    </span>
                </div>

                {isModule && d.childCount !== undefined && (
                    <div style={{
                        fontSize: 10,
                        color: '#64748b',
                        marginTop: 2,
                        marginLeft: 16,
                    }}>
                        {d.childCount} symbol{d.childCount !== 1 ? 's' : ''}
                    </div>
                )}

                <div style={{
                    position: 'absolute',
                    top: -8,
                    right: -4,
                    fontSize: 9,
                    color: d.color,
                    background: '#0f172a',
                    padding: '1px 5px',
                    borderRadius: 4,
                    border: `1px solid ${d.color}40`,
                    fontFamily: "'JetBrains Mono', monospace",
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                }}>
                    {d.symbolType === 'class' ? 'cls' : d.symbolType === 'function' ? 'fn' : d.symbolType === 'method' ? 'mtd' : d.symbolType}
                </div>
            </div>
            <Handle type="source" position={Position.Right} style={{ background: '#475569', border: 'none', width: 6, height: 6 }} />
        </>
    );
}

const nodeTypes: NodeTypes = {
    graphNode: GraphNode,
};

// ─── Metadata Panel ────────────────────────────────────

function MetadataPanel({ symbol, onClose }: { symbol: SymbolNode; onClose: () => void }) {
    return (
        <div style={{
            position: 'absolute',
            top: 16,
            right: 16,
            width: 300,
            background: '#1e293b',
            border: '1px solid #334155',
            borderRadius: 10,
            zIndex: 100,
            boxShadow: '0 20px 40px rgba(0,0,0,0.5)',
            overflow: 'hidden',
        }}>
            {/* Header */}
            <div style={{
                padding: '12px 16px',
                borderBottom: '1px solid #334155',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
            }}>
                <span style={{ color: '#f1f5f9', fontWeight: 600, fontSize: 13 }}>Symbol Details</span>
                <button
                    onClick={onClose}
                    style={{
                        background: '#334155',
                        border: 'none',
                        color: '#94a3b8',
                        cursor: 'pointer',
                        width: 24,
                        height: 24,
                        borderRadius: 6,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: 14,
                    }}
                >
                    ×
                </button>
            </div>

            {/* Body */}
            <div style={{ padding: '12px 16px', fontSize: 12 }}>
                <MetaRow label="Name" value={symbol.name} />
                {symbol.qualified_name && <MetaRow label="Qualified" value={symbol.qualified_name} />}
                <MetaRow label="Type" value={symbol.type} highlight />
                <MetaRow label="File" value={symbol.file} />
                <MetaRow label="Lines" value={`${symbol.start_line} – ${symbol.end_line}`} />
                <MetaRow label="Span" value={`${symbol.end_line - symbol.start_line + 1} lines`} />
            </div>
        </div>
    );
}

function MetaRow({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
    return (
        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid #1e293b50' }}>
            <span style={{ color: '#64748b' }}>{label}</span>
            <span style={{
                color: highlight ? '#818cf8' : '#cbd5e1',
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 11,
                maxWidth: 180,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                textAlign: 'right',
            }}>
                {value}
            </span>
        </div>
    );
}

// ─── Main Component ────────────────────────────────────

interface GraphViewerProps {
    scanId: string;
}

export function GraphViewer({ scanId }: GraphViewerProps) {
    const [graphData, setGraphData] = useState<GraphResponse | null>(null);
    const [viewMode, setViewMode] = useState<ViewMode>('file');
    const [selectedSymbol, setSelectedSymbol] = useState<SymbolNode | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState<FlowEdge>([]);

    // Fetch graph data
    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        setError(null);

        apiService.getGraph(scanId).then(data => {
            if (!cancelled) {
                setGraphData(data);
                setLoading(false);
            }
        }).catch(err => {
            if (!cancelled) {
                setError(err.message);
                setLoading(false);
            }
        });

        return () => { cancelled = true; };
    }, [scanId]);

    // Transform data when viewMode or data changes
    useEffect(() => {
        if (!graphData) return;
        const { nodes: n, edges: e, cycleNodeIds } = transformGraph(graphData, viewMode);

        // Mark cycle nodes
        const markedNodes = n.map(node => {
            if (cycleNodeIds.has(node.id)) {
                return {
                    ...node,
                    data: { ...node.data, color: '#ef4444' },
                    style: { ...(node.style || {}), filter: 'drop-shadow(0 0 6px rgba(239,68,68,0.4))' },
                };
            }
            return node;
        });

        setNodes(markedNodes);
        setEdges(e);
    }, [graphData, viewMode, setNodes, setEdges]);

    // Node click handler
    const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
        const data = node.data as GraphNodeData;
        if (data?.symbol) {
            setSelectedSymbol(data.symbol);
        }
    }, []);

    const stats = useMemo(() => {
        if (!graphData) return null;
        return {
            files: graphData.total_files,
            symbols: graphData.total_symbols,
            edges: graphData.total_edges,
            cycles: graphData.circular_dependencies.length,
        };
    }, [graphData]);

    // ─── Loading state ──────────────────────────────

    if (loading) {
        return (
            <div style={{
                height: 500,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: '#0f172a',
                borderRadius: 12,
                border: '1px solid #1e293b',
            }}>
                <div style={{ textAlign: 'center' }}>
                    <div style={{
                        width: 36,
                        height: 36,
                        border: '3px solid #1e293b',
                        borderTopColor: '#3b82f6',
                        borderRadius: '50%',
                        animation: 'spin 0.8s linear infinite',
                        margin: '0 auto 12px',
                    }} />
                    <p style={{ color: '#64748b', fontSize: 13 }}>Building structural graph…</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div style={{
                padding: 24,
                background: '#1e0000',
                borderRadius: 12,
                border: '1px solid #7f1d1d',
                color: '#fca5a5',
                fontSize: 13,
                textAlign: 'center',
            }}>
                ⚠️ {error}
            </div>
        );
    }

    if (!graphData || graphData.total_symbols === 0) {
        return (
            <div style={{
                padding: 24,
                background: '#0f172a',
                borderRadius: 12,
                border: '1px solid #1e293b',
                color: '#64748b',
                fontSize: 13,
                textAlign: 'center',
            }}>
                No graph data available. Scan completed with no supported source files.
            </div>
        );
    }

    return (
        <div style={{ position: 'relative' }}>
            {/* Toolbar */}
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: 12,
                flexWrap: 'wrap',
                gap: 12,
            }}>
                {/* View Mode Toggle */}
                <div style={{
                    display: 'flex',
                    gap: 2,
                    background: '#0f172a',
                    borderRadius: 8,
                    padding: 3,
                    border: '1px solid #1e293b',
                }}>
                    {(['file', 'symbol'] as ViewMode[]).map(mode => (
                        <button
                            key={mode}
                            onClick={() => setViewMode(mode)}
                            style={{
                                padding: '6px 14px',
                                borderRadius: 6,
                                border: 'none',
                                cursor: 'pointer',
                                fontSize: 12,
                                fontWeight: 500,
                                background: viewMode === mode ? '#3b82f6' : 'transparent',
                                color: viewMode === mode ? '#fff' : '#64748b',
                                transition: 'all 0.15s',
                            }}
                        >
                            {mode === 'file' ? '📁 File-Level' : '🔬 Symbol-Level'}
                        </button>
                    ))}
                </div>

                {/* Stats */}
                {stats && (
                    <div style={{ display: 'flex', gap: 16, fontSize: 11, color: '#64748b' }}>
                        <span><strong style={{ color: '#3b82f6' }}>{stats.files}</strong> files</span>
                        <span><strong style={{ color: '#8b5cf6' }}>{stats.symbols}</strong> symbols</span>
                        <span><strong style={{ color: '#f59e0b' }}>{stats.edges}</strong> edges</span>
                        {stats.cycles > 0 && (
                            <span style={{ color: '#ef4444' }}>
                                <strong>{stats.cycles}</strong> cycle{stats.cycles !== 1 ? 's' : ''}
                            </span>
                        )}
                    </div>
                )}
            </div>

            {/* Graph Canvas */}
            <div style={{
                height: 550,
                borderRadius: 12,
                border: '1px solid #1e293b',
                overflow: 'hidden',
                background: '#0f172a',
            }}>
                <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    onNodeClick={onNodeClick}
                    nodeTypes={nodeTypes}
                    fitView
                    fitViewOptions={{ padding: 0.3 }}
                    minZoom={0.2}
                    maxZoom={2.5}
                    proOptions={{ hideAttribution: true }}
                    style={{ background: '#0f172a' }}
                >
                    <Background color="#1e293b" gap={20} size={1} />
                    <Controls
                        showInteractive={false}
                        style={{
                            background: '#1e293b',
                            border: '1px solid #334155',
                            borderRadius: 8,
                        }}
                    />
                    <MiniMap
                        nodeColor={(n) => {
                            const d = n.data as GraphNodeData;
                            return d?.color || '#475569';
                        }}
                        style={{
                            background: '#0f172a',
                            border: '1px solid #1e293b',
                            borderRadius: 8,
                        }}
                        maskColor="rgba(15, 23, 42, 0.7)"
                    />
                </ReactFlow>
            </div>

            {/* Metadata Panel */}
            {selectedSymbol && (
                <MetadataPanel
                    symbol={selectedSymbol}
                    onClose={() => setSelectedSymbol(null)}
                />
            )}

            {/* Legend */}
            <div style={{
                display: 'flex',
                gap: 16,
                marginTop: 10,
                fontSize: 10,
                color: '#475569',
                flexWrap: 'wrap',
            }}>
                <LegendItem color="#3b82f6" label="Module" />
                <LegendItem color="#8b5cf6" label="Class" />
                <LegendItem color="#10b981" label="Function" />
                <LegendItem color="#14b8a6" label="Method" />
                <span style={{ margin: '0 4px', color: '#1e293b' }}>|</span>
                <LegendItem color="#3b82f6" label="imports" line />
                <LegendItem color="#f59e0b" label="calls" line />
                <LegendItem color="#ef4444" label="cycle" line />
            </div>
        </div>
    );
}

function LegendItem({ color, label, line }: { color: string; label: string; line?: boolean }) {
    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            {line ? (
                <div style={{ width: 14, height: 2, background: color, borderRadius: 1 }} />
            ) : (
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: color }} />
            )}
            <span>{label}</span>
        </div>
    );
}
