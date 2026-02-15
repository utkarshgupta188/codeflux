import React, { useState, useEffect } from 'react';
import { apiService } from '../services/repoService';

interface DiffViewerProps {
    scanId: string;
}

interface FileDiff {
    file: string;
    status: 'added' | 'removed' | 'modified';
    symbols_added: number;
    symbols_removed: number;
    symbols_modified: number;
}

interface DiffResponse {
    base_scan_id: string;
    head_scan_id: string;
    files_changed: FileDiff[];
    total_files_added: number;
    total_files_removed: number;
    total_files_modified: number;
    symbols_changed: number;
}

export const DiffViewer: React.FC<DiffViewerProps> = ({ scanId }) => {
    const [versions, setVersions] = useState<any[]>([]);
    const [baseScanId, setBaseScanId] = useState('');
    const [headScanId, setHeadScanId] = useState('');
    const [diff, setDiff] = useState<DiffResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        loadVersions();
    }, [scanId]);

    const loadVersions = async () => {
        try {
            const data = await apiService.getVersions(scanId);
            setVersions(data);
            if (data.length >= 2) {
                setHeadScanId(data[0].scan_id);
                setBaseScanId(data[1].scan_id);
            }
        } catch (err) {
            console.error('Failed to load versions:', err);
        }
    };

    const handleCompare = async () => {
        if (!baseScanId || !headScanId) return;

        setLoading(true);
        setError(null);

        try {
            const response = await fetch('http://localhost:8000/repo/diff', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    base_scan_id: baseScanId,
                    head_scan_id: headScanId,
                }),
            });

            if (!response.ok) throw new Error('Diff comparison failed');
            const data = await response.json();
            setDiff(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Comparison failed');
        } finally {
            setLoading(false);
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'added': return 'text-green-400 bg-green-900/20 border-green-800';
            case 'removed': return 'text-red-400 bg-red-900/20 border-red-800';
            case 'modified': return 'text-yellow-400 bg-yellow-900/20 border-yellow-800';
            default: return 'text-gray-400 bg-gray-900/20 border-gray-800';
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'added': return '+';
            case 'removed': return '-';
            case 'modified': return '~';
            default: return '?';
        }
    };

    return (
        <div className="bg-slate-900 text-slate-100 p-6 rounded-xl shadow-lg border border-slate-700/50">
            <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
                <span>🔄</span>
                Code Diff Viewer
            </h2>

            {versions.length < 2 ? (
                <div className="text-center py-12 text-slate-500">
                    <p className="text-lg mb-2">📊</p>
                    <p>Scan the repository multiple times to compare versions</p>
                    <p className="text-sm mt-2">Currently {versions.length} version(s) available</p>
                </div>
            ) : (
                <>
                    {/* Version Selector */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-2">
                                Base Version
                            </label>
                            <select
                                value={baseScanId}
                                onChange={(e) => setBaseScanId(e.target.value)}
                                className="w-full bg-slate-800 border-slate-700 text-slate-100 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
                            >
                                {versions.map((v) => (
                                    <option key={v.scan_id} value={v.scan_id}>
                                        {v.commit_hash?.substring(0, 7) || v.scan_id.substring(0, 8)} - {new Date(v.created_at).toLocaleString()}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-2">
                                Head Version
                            </label>
                            <select
                                value={headScanId}
                                onChange={(e) => setHeadScanId(e.target.value)}
                                className="w-full bg-slate-800 border-slate-700 text-slate-100 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
                            >
                                {versions.map((v) => (
                                    <option key={v.scan_id} value={v.scan_id}>
                                        {v.commit_hash?.substring(0, 7) || v.scan_id.substring(0, 8)} - {new Date(v.created_at).toLocaleString()}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div className="flex items-end">
                            <button
                                onClick={handleCompare}
                                disabled={loading || !baseScanId || !headScanId}
                                className="w-full px-6 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors font-medium"
                            >
                                {loading ? 'Comparing...' : 'Compare'}
                            </button>
                        </div>
                    </div>

                    {/* Error */}
                    {error && (
                        <div className="bg-red-900/20 border border-red-800 text-red-300 p-4 rounded-lg mb-4">
                            Error: {error}
                        </div>
                    )}

                    {/* Diff Results */}
                    {diff && (
                        <div className="space-y-4">
                            {/* Summary */}
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                <div className="bg-green-900/20 border border-green-800 rounded-lg p-3">
                                    <div className="text-green-400 text-2xl font-bold">{diff.total_files_added}</div>
                                    <div className="text-sm text-slate-400">Files Added</div>
                                </div>
                                <div className="bg-red-900/20 border border-red-800 rounded-lg p-3">
                                    <div className="text-red-400 text-2xl font-bold">{diff.total_files_removed}</div>
                                    <div className="text-sm text-slate-400">Files Removed</div>
                                </div>
                                <div className="bg-yellow-900/20 border border-yellow-800 rounded-lg p-3">
                                    <div className="text-yellow-400 text-2xl font-bold">{diff.total_files_modified}</div>
                                    <div className="text-sm text-slate-400">Files Modified</div>
                                </div>
                                <div className="bg-indigo-900/20 border border-indigo-800 rounded-lg p-3">
                                    <div className="text-indigo-400 text-2xl font-bold">{diff.symbols_changed}</div>
                                    <div className="text-sm text-slate-400">Symbols Changed</div>
                                </div>
                            </div>

                            {/* File Changes */}
                            <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                                <h3 className="text-lg font-semibold mb-3">Changed Files</h3>
                                <div className="space-y-2 max-h-[500px] overflow-y-auto">
                                    {diff.files_changed.length === 0 ? (
                                        <p className="text-slate-500 text-center py-4">No changes detected</p>
                                    ) : (
                                        diff.files_changed.map((file, idx) => (
                                            <div
                                                key={idx}
                                                className={`flex items-center justify-between p-3 rounded-lg border ${getStatusColor(file.status)}`}
                                            >
                                                <div className="flex items-center gap-3 flex-1 min-w-0">
                                                    <span className="text-lg font-mono font-bold">
                                                        {getStatusIcon(file.status)}
                                                    </span>
                                                    <span className="font-mono text-sm truncate">{file.file}</span>
                                                </div>
                                                <div className="flex gap-3 text-xs font-mono">
                                                    {file.symbols_added > 0 && (
                                                        <span className="text-green-400">+{file.symbols_added}</span>
                                                    )}
                                                    {file.symbols_removed > 0 && (
                                                        <span className="text-red-400">-{file.symbols_removed}</span>
                                                    )}
                                                    {file.symbols_modified > 0 && (
                                                        <span className="text-yellow-400">~{file.symbols_modified}</span>
                                                    )}
                                                </div>
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    );
};
