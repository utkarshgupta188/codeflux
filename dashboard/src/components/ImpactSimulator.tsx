/**
 * ImpactSimulator — visual change impact analysis panel.
 * Lets users select a file or symbol and see the blast radius.
 */

import { useState } from 'react';
import { apiService } from '../services/repoService';
import type { SimulateChangeResponse, AffectedSymbol } from '../types';

interface ImpactSimulatorProps {
    scanId: string;
}

const DEPTH_OPTIONS = [1, 2, 3, 4, 5, 7, 10];

const TYPE_COLORS: Record<string, string> = {
    module: '#3b82f6',
    class: '#8b5cf6',
    function: '#10b981',
    method: '#14b8a6',
};

function getRiskColor(score: number): string {
    if (score >= 15) return '#ef4444';
    if (score >= 8) return '#f59e0b';
    return '#10b981';
}

function getImpactColor(score: number): string {
    if (score >= 10) return '#ef4444';
    if (score >= 5) return '#f59e0b';
    return '#3b82f6';
}

export function ImpactSimulator({ scanId }: ImpactSimulatorProps) {
    const [file, setFile] = useState('');
    const [symbol, setSymbol] = useState('');
    const [depth, setDepth] = useState(5);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [result, setResult] = useState<SimulateChangeResponse | null>(null);

    const handleSimulate = async () => {
        const f = file.trim() || undefined;
        const s = symbol.trim() || undefined;
        if (!f && !s) return;

        setLoading(true);
        setError(null);
        setResult(null);

        try {
            const res = await apiService.simulateChange(scanId, f, s, depth);
            setResult(res);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Simulation failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{
            background: '#0f172a',
            border: '1px solid #1e293b',
            borderRadius: 12,
            overflow: 'hidden',
        }}>
            {/* Header */}
            <div style={{
                padding: '12px 16px',
                borderBottom: '1px solid #1e293b',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
            }}>
                <span style={{ fontSize: 16 }}>💥</span>
                <span style={{ color: '#e2e8f0', fontWeight: 600, fontSize: 13 }}>Change Impact Simulator</span>
                <span style={{
                    marginLeft: 'auto',
                    fontSize: 10,
                    color: '#475569',
                    background: '#1e293b',
                    padding: '2px 8px',
                    borderRadius: 4,
                    fontFamily: "'JetBrains Mono', monospace",
                }}>
                    deterministic
                </span>
            </div>

            {/* Input Form */}
            <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ display: 'flex', gap: 8 }}>
                    <div style={{ flex: 1 }}>
                        <label style={{ fontSize: 10, color: '#64748b', display: 'block', marginBottom: 4 }}>File path</label>
                        <input
                            type="text"
                            value={file}
                            onChange={(e) => setFile(e.target.value)}
                            placeholder="e.g. app/services/scanner.py"
                            style={{
                                width: '100%',
                                background: '#1e293b',
                                border: '1px solid #334155',
                                borderRadius: 6,
                                padding: '7px 10px',
                                color: '#e2e8f0',
                                fontSize: 11,
                                fontFamily: "'JetBrains Mono', monospace",
                                outline: 'none',
                                boxSizing: 'border-box',
                            }}
                        />
                    </div>
                    <div style={{ flex: 1 }}>
                        <label style={{ fontSize: 10, color: '#64748b', display: 'block', marginBottom: 4 }}>Symbol name</label>
                        <input
                            type="text"
                            value={symbol}
                            onChange={(e) => setSymbol(e.target.value)}
                            placeholder="e.g. GraphService"
                            style={{
                                width: '100%',
                                background: '#1e293b',
                                border: '1px solid #334155',
                                borderRadius: 6,
                                padding: '7px 10px',
                                color: '#e2e8f0',
                                fontSize: 11,
                                fontFamily: "'JetBrains Mono', monospace",
                                outline: 'none',
                                boxSizing: 'border-box',
                            }}
                        />
                    </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <label style={{ fontSize: 10, color: '#64748b' }}>Depth:</label>
                    <div style={{ display: 'flex', gap: 3 }}>
                        {DEPTH_OPTIONS.map(d => (
                            <button
                                key={d}
                                onClick={() => setDepth(d)}
                                style={{
                                    padding: '3px 8px',
                                    borderRadius: 4,
                                    border: 'none',
                                    cursor: 'pointer',
                                    fontSize: 10,
                                    fontWeight: depth === d ? 600 : 400,
                                    background: depth === d ? '#2563eb' : '#1e293b',
                                    color: depth === d ? '#fff' : '#64748b',
                                    transition: 'all 0.15s',
                                }}
                            >
                                {d}
                            </button>
                        ))}
                    </div>

                    <button
                        onClick={handleSimulate}
                        disabled={loading || (!file.trim() && !symbol.trim())}
                        style={{
                            marginLeft: 'auto',
                            padding: '6px 16px',
                            borderRadius: 6,
                            border: 'none',
                            cursor: loading || (!file.trim() && !symbol.trim()) ? 'default' : 'pointer',
                            fontSize: 11,
                            fontWeight: 600,
                            background: loading || (!file.trim() && !symbol.trim()) ? '#1e293b' : '#2563eb',
                            color: loading || (!file.trim() && !symbol.trim()) ? '#475569' : '#fff',
                            transition: 'all 0.15s',
                        }}
                    >
                        {loading ? '⏳ Simulating…' : '▶ Simulate'}
                    </button>
                </div>
            </div>

            {/* Error */}
            {error && (
                <div style={{ padding: '8px 16px', color: '#fca5a5', fontSize: 11, background: '#1e000050' }}>
                    ⚠️ {error}
                </div>
            )}

            {/* Results */}
            {result && (
                <div style={{ borderTop: '1px solid #1e293b' }}>
                    {/* Score Cards */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 1, background: '#1e293b' }}>
                        <ScoreCard
                            label="Impact Score"
                            value={result.impact_score.toFixed(1)}
                            color={getImpactColor(result.impact_score)}
                        />
                        <ScoreCard
                            label="Risk Increase"
                            value={`+${result.risk_increase.toFixed(1)}`}
                            color={getRiskColor(result.risk_increase)}
                        />
                        <ScoreCard
                            label="Affected"
                            value={String(result.total_affected)}
                            color="#8b5cf6"
                            sub={`${result.affected_files.length} files`}
                        />
                        <ScoreCard
                            label="Max Depth"
                            value={String(result.max_depth)}
                            color="#f59e0b"
                            sub={result.circular_risk ? '⚠ cycle risk' : undefined}
                        />
                    </div>

                    {/* Affected Files */}
                    <div style={{ padding: '12px 16px' }}>
                        <div style={{ fontSize: 11, color: '#64748b', marginBottom: 6, fontWeight: 600 }}>
                            Affected Files ({result.affected_files.length})
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                            {result.affected_files.map((f, i) => (
                                <span
                                    key={i}
                                    style={{
                                        background: '#1e293b',
                                        border: '1px solid #334155',
                                        borderRadius: 4,
                                        padding: '2px 8px',
                                        fontSize: 10,
                                        color: '#94a3b8',
                                        fontFamily: "'JetBrains Mono', monospace",
                                    }}
                                >
                                    {f}
                                </span>
                            ))}
                        </div>
                    </div>

                    {/* Affected Symbols Table */}
                    <div style={{ padding: '0 16px 12px' }}>
                        <div style={{ fontSize: 11, color: '#64748b', marginBottom: 6, fontWeight: 600 }}>
                            Affected Symbols ({result.affected_symbols.length})
                        </div>
                        <div style={{
                            maxHeight: 200,
                            overflowY: 'auto',
                            borderRadius: 6,
                            border: '1px solid #1e293b',
                        }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 10 }}>
                                <thead>
                                    <tr style={{ background: '#1e293b' }}>
                                        <th style={thStyle}>Symbol</th>
                                        <th style={thStyle}>Type</th>
                                        <th style={thStyle}>File</th>
                                        <th style={{ ...thStyle, textAlign: 'center' }}>Depth</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {result.affected_symbols.slice(0, 30).map((s: AffectedSymbol, i: number) => (
                                        <tr key={i} style={{ borderBottom: '1px solid #0f172a' }}>
                                            <td style={tdStyle}>
                                                <span style={{ color: '#e2e8f0', fontFamily: "'JetBrains Mono', monospace" }}>
                                                    {s.name}
                                                </span>
                                            </td>
                                            <td style={tdStyle}>
                                                <span style={{
                                                    color: TYPE_COLORS[s.type] || '#94a3b8',
                                                    fontSize: 9,
                                                    textTransform: 'uppercase',
                                                    fontWeight: 600,
                                                }}>
                                                    {s.type}
                                                </span>
                                            </td>
                                            <td style={{ ...tdStyle, color: '#64748b', fontFamily: "'JetBrains Mono', monospace" }}>
                                                {s.file}
                                            </td>
                                            <td style={{ ...tdStyle, textAlign: 'center' }}>
                                                <span style={{
                                                    background: s.depth <= 1 ? '#ef444430' : s.depth <= 2 ? '#f59e0b30' : '#3b82f630',
                                                    color: s.depth <= 1 ? '#ef4444' : s.depth <= 2 ? '#f59e0b' : '#3b82f6',
                                                    padding: '1px 6px',
                                                    borderRadius: 4,
                                                    fontSize: 9,
                                                    fontWeight: 600,
                                                }}>
                                                    {s.depth}
                                                </span>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                            {result.affected_symbols.length > 30 && (
                                <div style={{ textAlign: 'center', padding: 6, fontSize: 10, color: '#475569' }}>
                                    +{result.affected_symbols.length - 30} more symbols
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Empty state */}
            {!result && !loading && !error && (
                <div style={{ padding: '20px 16px', textAlign: 'center', color: '#334155', fontSize: 11 }}>
                    Enter a file path or symbol name and click Simulate to analyze blast radius.
                </div>
            )}
        </div>
    );
}

// ─── Sub-components ──────────────────────────────────────

function ScoreCard({ label, value, color, sub }: { label: string; value: string; color: string; sub?: string }) {
    return (
        <div style={{ background: '#0f172a', padding: '10px 14px', textAlign: 'center' }}>
            <div style={{ fontSize: 10, color: '#475569', marginBottom: 3 }}>{label}</div>
            <div style={{ fontSize: 20, fontWeight: 700, color, fontFamily: "'JetBrains Mono', monospace" }}>
                {value}
            </div>
            {sub && <div style={{ fontSize: 9, color: '#64748b', marginTop: 1 }}>{sub}</div>}
        </div>
    );
}

const thStyle: React.CSSProperties = {
    padding: '6px 10px',
    textAlign: 'left' as const,
    color: '#64748b',
    fontWeight: 600,
    fontSize: 9,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
};

const tdStyle: React.CSSProperties = {
    padding: '5px 10px',
    background: '#0f172a',
    fontSize: 10,
    color: '#94a3b8',
};
