import React, { useState } from 'react';
import { apiService } from '../services/repoService';

interface DiffViewerProps {
    repoId: string;
    versions: any[];
}

export const DiffViewer: React.FC<DiffViewerProps> = ({ repoId, versions }) => {
    const [base, setBase] = useState<string>('');
    const [head, setHead] = useState<string>('');
    const [diff, setDiff] = useState<any>(null);
    const [loading, setLoading] = useState(false);

    const handleCompare = async () => {
        if (!base || !head) return;
        setLoading(true);
        try {
            const result = await apiService.getDiff(repoId, base, head);
            setDiff(result);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="card p-6 mt-6">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
                <span className="text-purple-400">⚡</span> Version Comparison
            </h3>

            <div className="flex gap-4 mb-4 items-end">
                <div className="flex-1">
                    <label className="text-xs text-gray-500 uppercase block mb-1">Base Version</label>
                    <select
                        value={base}
                        onChange={(e) => setBase(e.target.value)}
                        className="input w-full"
                    >
                        <option value="">Select base...</option>
                        {versions.map((v: any) => (
                            <option key={v.id} value={v.id}>
                                {v.commit_hash.substring(0, 7)} ({new Date(v.created_at).toLocaleTimeString()})
                            </option>
                        ))}
                    </select>
                </div>
                <div className="flex-1">
                    <label className="text-xs text-gray-500 uppercase block mb-1">Head Version</label>
                    <select
                        value={head}
                        onChange={(e) => setHead(e.target.value)}
                        className="input w-full"
                    >
                        <option value="">Select head...</option>
                        {versions.map((v: any) => (
                            <option key={v.id} value={v.id}>
                                {v.commit_hash.substring(0, 7)} ({new Date(v.created_at).toLocaleTimeString()})
                            </option>
                        ))}
                    </select>
                </div>
                <button
                    onClick={handleCompare}
                    disabled={!base || !head || loading}
                    className="btn btn-primary h-[42px]"
                >
                    {loading ? 'Analyzing...' : 'Compare'}
                </button>
            </div>

            {diff && (
                <div className="grid grid-cols-3 gap-6 animate-fade-in">
                    <div className="bg-gray-800/50 p-4 rounded-lg border border-gray-700">
                        <h4 className="font-semibold mb-3 text-green-400">Added Files ({diff.added_files.length})</h4>
                        <ul className="text-sm space-y-1 max-h-40 overflow-y-auto">
                            {diff.added_files.map((f: string) => (
                                <li key={f} className="truncate" title={f}>+ {f}</li>
                            ))}
                            {diff.added_files.length === 0 && <li className="text-gray-500 italic">None</li>}
                        </ul>
                    </div>

                    <div className="bg-gray-800/50 p-4 rounded-lg border border-gray-700">
                        <h4 className="font-semibold mb-3 text-red-400">Removed Files ({diff.removed_files.length})</h4>
                        <ul className="text-sm space-y-1 max-h-40 overflow-y-auto">
                            {diff.removed_files.map((f: string) => (
                                <li key={f} className="truncate" title={f}>- {f}</li>
                            ))}
                            {diff.removed_files.length === 0 && <li className="text-gray-500 italic">None</li>}
                        </ul>
                    </div>

                    <div className="bg-gray-800/50 p-4 rounded-lg border border-gray-700">
                        <h4 className="font-semibold mb-3 text-blue-400">Metrics Delta</h4>
                        <div className="space-y-2 text-sm">
                            <div className="flex justify-between">
                                <span>Complexity:</span>
                                <span className={diff.complexity_delta > 0 ? "text-red-400" : "text-green-400"}>
                                    {diff.complexity_delta > 0 ? '+' : ''}{diff.complexity_delta}
                                </span>
                            </div>
                            <div className="flex justify-between">
                                <span>Risk Score:</span>
                                <span className={diff.risk_delta > 0 ? "text-red-400" : "text-green-400"}>
                                    {diff.risk_delta > 0 ? '+' : ''}{diff.risk_delta}
                                </span>
                            </div>
                            <div className="flex justify-between">
                                <span>Dependency Changes:</span>
                                <span>{diff.dependency_changes.length}</span>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
