import React, { useEffect, useState } from 'react';
import { repoService } from '../services/repoService';
import type { RepoHealth } from '../types';

interface Props {
    repoId: string;
}

export const HealthDashboard: React.FC<Props> = ({ repoId }) => {
    const [health, setHealth] = useState<RepoHealth | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [exporting, setExporting] = useState(false);

    useEffect(() => {
        const fetchHealth = async () => {
            try {
                setError(null);
                const data = await repoService.getRepoHealth(repoId);
                setHealth(data);
            } catch (err) {
                setError('Failed to load health metrics');
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        if (repoId) fetchHealth();
    }, [repoId]);

    const handleExport = async (format: 'json' | 'markdown' | 'html') => {
        setExporting(true);
        try {
            const response = await fetch(`http://localhost:8000/repo/${repoId}/export`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    format,
                    include_graph: true,
                    include_health: true,
                    include_hotspots: true,
                }),
            });

            if (!response.ok) throw new Error('Export failed');

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `codeflux-report-${repoId}.${format === 'markdown' ? 'md' : format}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (err) {
            console.error('Export failed:', err);
            alert('Export failed. Please try again.');
        } finally {
            setExporting(false);
        }
    };

    if (loading) {
        return (
            <div className="text-center py-12">
                <svg className="animate-spin h-8 w-8 mx-auto text-primary-500 mb-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
                <p className="text-gray-500 text-sm">Loading health metrics...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-4 bg-red-900/20 border border-red-800/30 rounded-lg text-red-300 text-sm text-center">
                {error}
            </div>
        );
    }

    if (!health) return null;

    const riskGradient = health.riskScore < 30
        ? 'from-green-500 to-emerald-600'
        : health.riskScore < 70
            ? 'from-yellow-500 to-orange-500'
            : 'from-red-500 to-rose-600';

    return (
        <div className="space-y-6">
            {/* Export Buttons */}
            <div className="flex justify-end gap-2">
                <button
                    onClick={() => handleExport('json')}
                    disabled={exporting}
                    className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 rounded-lg text-sm transition-colors"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Export JSON
                </button>
                <button
                    onClick={() => handleExport('markdown')}
                    disabled={exporting}
                    className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 rounded-lg text-sm transition-colors"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Export MD
                </button>
                <button
                    onClick={() => handleExport('html')}
                    disabled={exporting}
                    className="flex items-center gap-2 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-lg text-sm transition-colors"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Export HTML
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Risk Score Card */}
                <div className="card md:col-span-1 relative overflow-hidden">
                    <div className="absolute top-0 right-0 p-3 opacity-5 text-9xl font-black leading-none select-none pointer-events-none">
                        {health.riskScore}
                    </div>

                    <h3 className="text-gray-400 font-medium tracking-wide uppercase text-xs mb-1">Risk Score</h3>

                    <div className="flex items-end gap-3 mt-2">
                        <div className={`text-6xl font-black bg-gradient-to-r ${riskGradient} bg-clip-text text-transparent`}>
                            {health.riskScore}
                        </div>
                        <div className="text-sm text-gray-500 mb-2">/ 100</div>
                    </div>

                    {/* Risk Bar */}
                    <div className="mt-4 h-2 w-full bg-dark-700 rounded-full overflow-hidden">
                        <div
                            className={`h-full bg-gradient-to-r ${riskGradient} rounded-full transition-all duration-1000`}
                            style={{ width: `${health.riskScore}%` }}
                        />
                    </div>

                    <div className="mt-4 pt-3 border-t border-dark-700 flex justify-between text-sm">
                        <span className="text-gray-500">Avg Complexity</span>
                        <span className="text-white font-mono font-semibold">{health.complexityScore}</span>
                    </div>
                </div>

                {/* Details Grid */}
                <div className="md:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-6">
                    {/* Circular Dependencies */}
                    <div className="card">
                        <div className="flex items-center gap-2 mb-3">
                            <svg className="w-5 h-5 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                            </svg>
                            <h3 className="text-gray-400 text-xs uppercase tracking-wider">Circular Deps</h3>
                        </div>
                        <div className="text-4xl font-bold text-white mb-2">{health.circularDependencies}</div>
                        <p className="text-xs text-gray-600 leading-relaxed">
                            Cycles detected in import graph. High count = tightly coupled architecture.
                        </p>
                    </div>

                    {/* Hotspots */}
                    <div className="card row-span-2">
                        <div className="flex items-center gap-2 mb-4">
                            <svg className="w-5 h-5 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z" />
                            </svg>
                            <h3 className="text-gray-400 text-xs uppercase tracking-wider">Top Hotspots</h3>
                        </div>
                        <div className="space-y-2.5">
                            {health.hotspots.length === 0 && (
                                <p className="text-gray-600 text-sm italic">No hotspots detected</p>
                            )}
                            {health.hotspots.map((hotspot, idx) => (
                                <div key={idx} className="flex items-center justify-between group hover:bg-dark-700/50 rounded-md px-2 py-1.5 -mx-2 transition-colors">
                                    <div className="flex items-center gap-2.5 overflow-hidden min-w-0">
                                        <span className={`text-xs font-mono w-5 text-center flex-shrink-0 ${idx === 0 ? 'text-red-400' : idx === 1 ? 'text-orange-400' : 'text-gray-600'}`}>
                                            #{idx + 1}
                                        </span>
                                        <span className="text-sm text-gray-400 truncate group-hover:text-gray-200 transition-colors font-mono">
                                            {hotspot.file}
                                        </span>
                                    </div>
                                    <span className={`text-xs font-mono flex-shrink-0 ml-2 px-2 py-0.5 rounded-full border ${idx === 0 ? 'bg-red-900/30 text-red-400 border-red-800/50' :
                                        idx === 1 ? 'bg-orange-900/30 text-orange-400 border-orange-800/50' :
                                            'bg-dark-900 text-gray-400 border-dark-700'
                                        }`}>
                                        {hotspot.score}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
