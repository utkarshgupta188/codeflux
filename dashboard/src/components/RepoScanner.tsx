import React, { useState, useEffect, useMemo } from 'react';
import { repoService } from '../services/repoService';
import type { ScanResult, RepoScanRequest } from '../types';
import { DiffViewer } from './DiffViewer';

interface Props {
    onScanComplete: (repoId: string) => void;
}

export const RepoScanner: React.FC<Props> = ({ onScanComplete }) => {
    // ... (inside RepoScanner component)
    const [path, setPath] = useState('');
    const [source, setSource] = useState<RepoScanRequest['source']>('github');
    const [scanState, setScanState] = useState<ScanResult | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [versions, setVersions] = useState<any[]>([]);

    // Detect if running on localhost
    const isLocalhost = useMemo(() => {
        const host = window.location.hostname;
        return host === 'localhost' || host === '127.0.0.1' || host === '::1';
    }, []);

    // Default to local if on localhost, github otherwise
    useEffect(() => {
        setSource(isLocalhost ? 'local' : 'github');
    }, [isLocalhost]);

    // Fetch versions when scan completes
    const fetchVersions = async (repoId: string) => {
        try {
            const vs = await repoService.getVersions(repoId);
            setVersions(vs);
        } catch (err) {
            console.error(err);
        }
    };

    const startScan = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setScanState(null);
        setVersions([]); // Reset versions
        try {
            const result = await repoService.scanRepo({ path, source });
            setScanState(result);
        } catch (err) {
            setError('Failed to start scan. Is the backend running?');
            console.error(err);
        }
    };

    // Polling Effect
    useEffect(() => {
        if (!scanState || scanState.status === 'completed' || scanState.status === 'failed') return;

        const interval = setInterval(async () => {
            try {
                const update = await repoService.getScanStatus(scanState.scanId);
                setScanState(update);
                if (update.status === 'completed') {
                    onScanComplete(update.scanId);
                    // Attempt to fetch versions using scanId as a proxy for repoId?
                    // No, backend endpoint /repo/{id}/versions expects repo_id.
                    // I'll update backend to return repoId in ScanResult next.
                    // For now, assume update.scanId is what we have.
                    // Actually, let's query versions by scan_id if I change the backend.
                    // OR: I modify `ScanResult` in backend to include `repoId`.
                    if ((update as any).repoId) {
                        fetchVersions((update as any).repoId);
                    }
                }
            } catch (err) {
                console.error('Polling error', err);
            }
        }, 2000);

        return () => clearInterval(interval);
    }, [scanState, onScanComplete]);

    // We need repoId to fetch versions.
    // Currently ScanResult has scanId.
    // The backend `ScannerService.start_scan` returns `ScanResult` which has `scanId`.
    // The `_process_scan` creates a `Repository` which has `id` (repo_id).
    // But `ScanResult` struct doesn't have `repoId`.
    // I should fix backend `ScanResult` to include `repoId` when complete, OR lookup repo by scanId.
    // `main.py` has `GET /repo/{id}/versions` where id is `repo_id`.
    // `GET /repo/{id}/status` returns `ScanResult`.

    // Quick fix: Assuming for now we can't easily get repoId from scanId without backend change.
    // Let's update backend `ScannerService` to populate `repoId` in `ScanResult` when complete.
    // Actually, `RepoVersion.scan_id` is indexed.
    // So I can lookup `RepoVersion` by `scan_id` to getting `repo_id`.

    // Modification: I'll update `RepoScanner` to fetch versions using existing `repoId` if available?
    // No, I need the `repoId` from the scan.

    // Wait, the existing `onScanComplete(repoId)` prop implies the parent knows about `repoId`.
    // `App.tsx` passes `setSelectedRepo(id)`.
    // But how does `RepoScanner` know `repoId`?
    // `onScanComplete` is called with `update.scanId` in current code (lines 48).

    // I will verify `ScanResult` definition in backend.

    // For now, I'll paste the DiffViewer integration, but I suspect I might need to patch backend
    // to return `repoId` in `ScanResult`.

    const statusIcon = (status: string) => {
        switch (status) {
            case 'pending': return '⏳';
            case 'scanning': return '🔍';
            case 'completed': return '✅';
            case 'failed': return '❌';
            default: return '•';
        }
    };

    return (
        <div className="card max-w-2xl mx-auto relative overflow-hidden">
            {/* Decorative gradient */}
            <div className="absolute -top-24 -right-24 w-48 h-48 bg-primary-600/10 rounded-full blur-3xl pointer-events-none" />

            <div className="flex items-center gap-3 mb-6 border-b border-dark-700 pb-4">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary-500 to-blue-700 flex items-center justify-center">
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                </div>
                <div>
                    <h2 className="text-xl font-bold text-white">Repository Scanner</h2>
                    <p className="text-xs text-gray-500">Analyze any codebase for health metrics</p>
                </div>
            </div>

            <form onSubmit={startScan} className="space-y-4">
                <div className="flex gap-4">
                    {isLocalhost && (
                        <label className="flex items-center gap-2 cursor-pointer group">
                            <input
                                type="radio"
                                checked={source === 'local'}
                                onChange={() => { setSource('local'); setPath(''); }}
                                className="accent-primary-500"
                            />
                            <div className="flex items-center gap-1.5">
                                <svg className="w-4 h-4 text-gray-400 group-hover:text-primary-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                                </svg>
                                <span className="text-gray-300 text-sm">Local Path</span>
                            </div>
                        </label>
                    )}
                    <label className="flex items-center gap-2 cursor-pointer group">
                        <input
                            type="radio"
                            checked={source === 'github'}
                            onChange={() => { setSource('github'); setPath(''); }}
                            className="accent-primary-500"
                        />
                        <div className="flex items-center gap-1.5">
                            <svg className="w-4 h-4 text-gray-400 group-hover:text-primary-400 transition-colors" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                            </svg>
                            <span className="text-gray-300 text-sm">GitHub URL</span>
                        </div>
                    </label>
                </div>

                <div className="flex gap-2">
                    <div className="relative flex-1">
                        <input
                            type="text"
                            value={path}
                            onChange={(e) => setPath(e.target.value)}
                            placeholder={source === 'local' ? 'C:\\path\\to\\repo or /path/to/repo' : 'https://github.com/user/repo'}
                            className="input w-full pl-4 pr-4 py-3"
                            required
                        />
                    </div>
                    <button
                        type="submit"
                        disabled={!path || scanState?.status === 'scanning' || scanState?.status === 'pending'}
                        className="btn px-6 py-3 font-semibold whitespace-nowrap"
                    >
                        {scanState?.status === 'scanning' || scanState?.status === 'pending'
                            ? (
                                <span className="flex items-center gap-2">
                                    <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                                    </svg>
                                    Scanning…
                                </span>
                            )
                            : 'Scan'}
                    </button>
                </div>
            </form>

            {error && (
                <div className="mt-4 p-3 bg-red-900/30 text-red-300 rounded-lg border border-red-800/50 text-sm flex items-center gap-2">
                    <span>⚠️</span> {error}
                </div>
            )}

            {scanState && (
                <div className="mt-6 space-y-3">
                    <div className="flex items-center justify-between bg-dark-900/70 p-4 rounded-lg border border-dark-700">
                        <div className="flex items-center gap-3">
                            <span className="text-xl">{statusIcon(scanState.status)}</span>
                            <div>
                                <div className="text-xs text-gray-500 uppercase tracking-wide">Status</div>
                                <div className={`font-mono font-bold capitalize text-sm ${scanState.status === 'completed' ? 'text-green-400' :
                                    scanState.status === 'failed' ? 'text-red-400' : 'text-blue-400'
                                    }`}>
                                    {scanState.status}
                                </div>
                            </div>
                        </div>
                        {(scanState.status === 'scanning' || scanState.status === 'pending') && (
                            <div className="h-1.5 w-28 bg-dark-700 rounded-full overflow-hidden">
                                <div className="h-full bg-gradient-to-r from-primary-600 to-primary-500 animate-pulse rounded-full" style={{ width: scanState.status === 'pending' ? '30%' : '65%' }} />
                            </div>
                        )}
                    </div>

                    {scanState.error && (
                        <div className="p-3 bg-red-900/20 text-red-300 rounded-lg border border-red-800/30 text-sm font-mono">
                            {scanState.error}
                        </div>
                    )}

                    {scanState.stats && (
                        <div className="grid grid-cols-3 gap-2">
                            <StatItem label="Files" value={scanState.stats.files} icon="📄" />
                            <StatItem label="Symbols" value={scanState.stats.symbols} icon="🔣" />
                            <StatItem label="Deps" value={scanState.stats.dependencies} icon="📦" />
                        </div>
                    )}
                </div>
            )}

            {/* DiffViewer Integration */}
            {versions.length > 1 && versions[0]?.repo_id && (
                <div className="mt-8 border-t border-gray-700 pt-6">
                    <DiffViewer repoId={versions[0].repo_id} versions={versions} />
                </div>
            )}
        </div>
    );
};

const StatItem = ({ label, value, icon }: { label: string; value: number; icon: string }) => (
    <div className="bg-dark-900/70 p-3 rounded-lg border border-dark-700 text-center hover:border-primary-500/30 transition-colors">
        <div className="text-lg mb-1">{icon}</div>
        <div className="text-xs text-gray-500 uppercase tracking-wider">{label}</div>
        <div className="text-lg font-bold text-gray-200 font-mono">{value.toLocaleString()}</div>
    </div>
);
