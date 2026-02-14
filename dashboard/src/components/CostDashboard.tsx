/**
 * CostDashboard — real-time cost-aware routing metrics panel.
 * Shows provider costs, scoring weights, and routing policy state.
 */

import { useState, useEffect, useCallback } from 'react';
import { apiService } from '../services/repoService';
import type { CostMetricsResponse } from '../types';

export function CostDashboard() {
    const [data, setData] = useState<CostMetricsResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchData = useCallback(async () => {
        try {
            setError(null);
            const res = await apiService.getCostMetrics();
            setData(res);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 10000); // auto-refresh every 10s
        return () => clearInterval(interval);
    }, [fetchData]);

    if (loading && !data) {
        return (
            <div style={{ textAlign: 'center', padding: 40, color: '#475569' }}>
                ⏳ Loading cost metrics…
            </div>
        );
    }

    if (error && !data) {
        return (
            <div style={{ textAlign: 'center', padding: 40, color: '#fca5a5' }}>
                ⚠️ {error}
            </div>
        );
    }

    if (!data) return null;

    const providers = Object.entries(data.providers);
    const hasProviders = providers.length > 0;

    return (
        <div style={{
            background: '#0f172a',
            border: '1px solid #1e293b',
            borderRadius: 12,
            overflow: 'hidden',
        }}>
            {/* Header */}
            <div style={{
                padding: '14px 20px',
                borderBottom: '1px solid #1e293b',
                display: 'flex',
                alignItems: 'center',
                gap: 10,
            }}>
                <span style={{ fontSize: 18 }}>💰</span>
                <span style={{ color: '#e2e8f0', fontWeight: 600, fontSize: 14 }}>Cost-Aware Routing</span>
                <span style={{
                    fontSize: 10,
                    color: '#64748b',
                    background: '#1e293b',
                    padding: '2px 8px',
                    borderRadius: 4,
                    fontFamily: "'JetBrains Mono', monospace",
                }}>
                    {data.date}
                </span>
                <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <div style={{
                        width: 6, height: 6, borderRadius: '50%',
                        background: '#10b981',
                        animation: 'pulse 2s infinite',
                    }} />
                    <span style={{ fontSize: 10, color: '#475569' }}>live</span>
                </div>
            </div>

            {/* Provider Cards */}
            {hasProviders ? (
                <div style={{ display: 'grid', gridTemplateColumns: `repeat(${providers.length}, 1fr)`, gap: 1, background: '#1e293b' }}>
                    {providers.map(([name, info]) => {
                        const limit = data.policy.daily_limits[name] || 999;
                        const pct = Math.min((info.daily_cost_usd / limit) * 100, 100);
                        const overBudget = info.daily_cost_usd >= limit;
                        const costColor = overBudget ? '#ef4444' : pct > 60 ? '#f59e0b' : '#10b981';

                        return (
                            <div key={name} style={{ background: '#0f172a', padding: 16 }}>
                                {/* Provider name + status */}
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                                    <span style={{
                                        color: '#e2e8f0',
                                        fontWeight: 600,
                                        fontSize: 13,
                                        fontFamily: "'JetBrains Mono', monospace",
                                        textTransform: 'uppercase',
                                    }}>
                                        {name}
                                    </span>
                                    {overBudget && (
                                        <span style={{
                                            fontSize: 9,
                                            background: '#ef444430',
                                            color: '#ef4444',
                                            padding: '1px 6px',
                                            borderRadius: 4,
                                            fontWeight: 600,
                                        }}>
                                            OVER BUDGET
                                        </span>
                                    )}
                                </div>

                                {/* Cost bar */}
                                <div style={{ marginBottom: 12 }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                                        <span style={{ fontSize: 10, color: '#64748b' }}>Daily Cost</span>
                                        <span style={{
                                            fontSize: 11,
                                            fontFamily: "'JetBrains Mono', monospace",
                                            color: costColor,
                                            fontWeight: 600,
                                        }}>
                                            ${info.daily_cost_usd.toFixed(4)} / ${limit.toFixed(2)}
                                        </span>
                                    </div>
                                    <div style={{
                                        height: 4,
                                        background: '#1e293b',
                                        borderRadius: 2,
                                        overflow: 'hidden',
                                    }}>
                                        <div style={{
                                            height: '100%',
                                            width: `${pct}%`,
                                            background: costColor,
                                            borderRadius: 2,
                                            transition: 'width 0.5s ease',
                                        }} />
                                    </div>
                                </div>

                                {/* Stats grid */}
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                                    <MiniStat label="Requests" value={String(info.requests_today)} color="#3b82f6" />
                                    <MiniStat label="Failures" value={String(info.failures_today)} color={info.failures_today > 0 ? '#ef4444' : '#10b981'} />
                                    <MiniStat
                                        label="Avg Latency"
                                        value={`${info.avg_latency_ms.toFixed(0)}ms`}
                                        color={info.avg_latency_ms > data.policy.latency_spike_ms ? '#ef4444' : '#f59e0b'}
                                    />
                                    <MiniStat
                                        label="Fail Rate"
                                        value={`${(info.fallback_rate * 100).toFixed(1)}%`}
                                        color={info.fallback_rate > 0.2 ? '#ef4444' : '#10b981'}
                                    />
                                </div>
                            </div>
                        );
                    })}
                </div>
            ) : (
                <div style={{ padding: '24px 20px', textAlign: 'center', color: '#334155', fontSize: 12 }}>
                    No provider data yet. Send a chat request to start tracking costs.
                </div>
            )}

            {/* Policy Config */}
            <div style={{ borderTop: '1px solid #1e293b', padding: '12px 20px' }}>
                <div style={{ fontSize: 10, color: '#475569', fontWeight: 600, marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Routing Policy
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    <PolicyTag label="Latency Weight" value={data.policy.weights.latency.toString()} />
                    <PolicyTag label="Fallback Weight" value={data.policy.weights.fallback.toString()} />
                    <PolicyTag label="Cost Weight" value={data.policy.weights.cost.toString()} />
                    <PolicyTag label="Spike Threshold" value={`${data.policy.latency_spike_ms}ms`} />
                    {Object.entries(data.policy.cost_per_1k_tokens).map(([p, c]) => (
                        <PolicyTag key={p} label={`${p} $/1K`} value={`$${c}`} />
                    ))}
                </div>
            </div>
        </div>
    );
}

// ─── Sub-components ──────────────────────────────────────

function MiniStat({ label, value, color }: { label: string; value: string; color: string }) {
    return (
        <div style={{
            background: '#1e293b',
            borderRadius: 6,
            padding: '6px 8px',
            textAlign: 'center',
        }}>
            <div style={{ fontSize: 9, color: '#475569', marginBottom: 2 }}>{label}</div>
            <div style={{
                fontSize: 13,
                fontWeight: 700,
                color,
                fontFamily: "'JetBrains Mono', monospace",
            }}>
                {value}
            </div>
        </div>
    );
}

function PolicyTag({ label, value }: { label: string; value: string }) {
    return (
        <span style={{
            background: '#1e293b',
            border: '1px solid #334155',
            borderRadius: 4,
            padding: '3px 8px',
            fontSize: 10,
            color: '#94a3b8',
            fontFamily: "'JetBrains Mono', monospace",
        }}>
            <span style={{ color: '#475569' }}>{label}: </span>
            {value}
        </span>
    );
}
