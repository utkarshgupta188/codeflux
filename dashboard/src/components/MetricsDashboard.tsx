import React, { useEffect, useState } from 'react';
import { apiService } from '../services/repoService';
import type { MetricsSummary, TimeRange } from '../types';

export const MetricsDashboard: React.FC = () => {
    const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [range, setRange] = useState<TimeRange>('last_24h');

    const fetchMetrics = async () => {
        try {
            setLoading(true);
            setError(null);
            const data = await apiService.getMetrics(range);
            setMetrics(data);
        } catch (err) {
            setError('Failed to fetch metrics. Make sure the backend has some traffic logged.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchMetrics();
    }, [range]);

    const ranges: { value: TimeRange; label: string }[] = [
        { value: 'last_1h', label: '1 Hour' },
        { value: 'last_24h', label: '24 Hours' },
        { value: 'last_7d', label: '7 Days' },
    ];

    if (loading) {
        return (
            <div className="text-center py-12">
                <svg className="animate-spin h-8 w-8 mx-auto text-primary-500 mb-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                <p className="text-gray-500 text-sm">Loading metrics…</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="card max-w-2xl mx-auto text-center">
                <div className="text-yellow-400 text-4xl mb-3">📊</div>
                <p className="text-gray-400 text-sm mb-4">{error}</p>
                <button onClick={fetchMetrics} className="btn px-4 py-2 text-sm">Retry</button>
            </div>
        );
    }
    if (!metrics) return null;

    return (
        <div className="space-y-6 max-w-4xl mx-auto">
            {/* Time Range Selector */}
            <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold text-white">Gateway Metrics</h2>
                <div className="flex gap-1 bg-dark-800 rounded-lg p-1 border border-dark-700">
                    {ranges.map((r) => (
                        <button
                            key={r.value}
                            onClick={() => setRange(r.value)}
                            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${range === r.value
                                    ? 'bg-primary-600 text-white shadow-sm'
                                    : 'text-gray-400 hover:text-white'
                                }`}
                        >
                            {r.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <KPICard
                    label="Total Requests"
                    value={metrics.total_requests.toLocaleString()}
                    icon="📨"
                    color="text-blue-400"
                />
                <KPICard
                    label="Avg Latency"
                    value={`${metrics.avg_latency_ms.toFixed(0)}ms`}
                    icon="⚡"
                    color="text-yellow-400"
                />
                <KPICard
                    label="P95 Latency"
                    value={`${metrics.p95_latency_ms.toFixed(0)}ms`}
                    icon="📈"
                    color="text-orange-400"
                />
                <KPICard
                    label="Fallback Rate"
                    value={`${metrics.fallback_rate_percent.toFixed(1)}%`}
                    icon="🔄"
                    color={metrics.fallback_rate_percent > 20 ? 'text-red-400' : 'text-green-400'}
                />
            </div>

            {/* Provider Split */}
            <div className="card">
                <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Provider Distribution</h3>
                {metrics.provider_split.length === 0 ? (
                    <p className="text-gray-600 text-sm italic">No provider data available</p>
                ) : (
                    <div className="space-y-3">
                        {metrics.provider_split.map((split, idx) => (
                            <div key={idx}>
                                <div className="flex items-center justify-between mb-1">
                                    <span className="text-sm text-gray-300 font-mono">{split.provider}</span>
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs text-gray-500">{split.count} reqs</span>
                                        <span className="text-sm font-semibold text-white">{split.percentage.toFixed(1)}%</span>
                                    </div>
                                </div>
                                <div className="h-2 bg-dark-700 rounded-full overflow-hidden">
                                    <div
                                        className="h-full rounded-full transition-all duration-700 bg-gradient-to-r from-primary-600 to-blue-500"
                                        style={{ width: `${split.percentage}%` }}
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

const KPICard = ({ label, value, icon, color }: { label: string; value: string; icon: string; color: string }) => (
    <div className="card text-center hover:border-primary-500/30 transition-colors">
        <div className="text-2xl mb-2">{icon}</div>
        <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</div>
        <div className={`text-2xl font-bold font-mono ${color}`}>{value}</div>
    </div>
);
