import React, { useState } from 'react';
import { apiService } from '../services/repoService';

interface SearchResult {
    file: string;
    line: number;
    content: string;
    symbol?: string;
    symbol_type?: string;
}

interface SearchResponse {
    results: SearchResult[];
    total_matches: number;
    truncated: boolean;
}

interface CodeSearchProps {
    scanId: string;
}

export const CodeSearch: React.FC<CodeSearchProps> = ({ scanId }) => {
    const [query, setQuery] = useState('');
    const [fileType, setFileType] = useState('');
    const [symbolType, setSymbolType] = useState('');
    const [caseSensitive, setCaseSensitive] = useState(false);
    const [useRegex, setUseRegex] = useState(false);
    const [results, setResults] = useState<SearchResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;

        setLoading(true);
        setError(null);

        try {
            const data = await apiService.searchCode(scanId, {
                query: query.trim(),
                file_type: fileType || null,
                symbol_type: symbolType || null,
                case_sensitive: caseSensitive,
                regex: useRegex,
                limit: 100,
            });
            setResults(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Search failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="bg-slate-900 text-slate-100 p-6 rounded-xl shadow-lg border border-slate-700/50">
            <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
                <span>🔍</span>
                Code Search
            </h2>

            {/* Search Form */}
            <form onSubmit={handleSearch} className="space-y-4 mb-6">
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Search code..."
                        className="flex-1 bg-slate-800 border-slate-700 text-slate-100 rounded-lg px-4 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
                    />
                    <button
                        type="submit"
                        disabled={loading || !query.trim()}
                        className="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors font-medium"
                    >
                        {loading ? 'Searching...' : 'Search'}
                    </button>
                </div>

                {/* Filters */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <select
                        value={fileType}
                        onChange={(e) => setFileType(e.target.value)}
                        className="bg-slate-800 border-slate-700 text-slate-100 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                        <option value="">All Files</option>
                        <option value="python">Python</option>
                        <option value="javascript">JavaScript</option>
                        <option value="typescript">TypeScript</option>
                        <option value="java">Java</option>
                        <option value="go">Go</option>
                        <option value="rust">Rust</option>
                        <option value="cpp">C++</option>
                        <option value="c">C</option>
                    </select>

                    <select
                        value={symbolType}
                        onChange={(e) => setSymbolType(e.target.value)}
                        className="bg-slate-800 border-slate-700 text-slate-100 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                        <option value="">All Symbols</option>
                        <option value="function">Functions</option>
                        <option value="class">Classes</option>
                        <option value="method">Methods</option>
                        <option value="module">Modules</option>
                    </select>

                    <label className="flex items-center gap-2 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 cursor-pointer hover:bg-slate-700/50">
                        <input
                            type="checkbox"
                            checked={caseSensitive}
                            onChange={(e) => setCaseSensitive(e.target.checked)}
                            className="rounded"
                        />
                        <span className="text-sm">Case Sensitive</span>
                    </label>

                    <label className="flex items-center gap-2 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 cursor-pointer hover:bg-slate-700/50">
                        <input
                            type="checkbox"
                            checked={useRegex}
                            onChange={(e) => setUseRegex(e.target.checked)}
                            className="rounded"
                        />
                        <span className="text-sm">Regex</span>
                    </label>
                </div>
            </form>

            {/* Error */}
            {error && (
                <div className="bg-red-900/20 border border-red-800 text-red-300 p-4 rounded-lg mb-4">
                    Error: {error}
                </div>
            )}

            {/* Results */}
            {results && (
                <div className="space-y-4">
                    <div className="flex items-center justify-between text-sm text-slate-400 pb-2 border-b border-slate-700">
                        <span>
                            Found {results.total_matches} match{results.total_matches !== 1 ? 'es' : ''}
                            {results.truncated && ` (showing first 100)`}
                        </span>
                        <span>{results.results.length} results</span>
                    </div>

                    {results.results.length === 0 ? (
                        <div className="text-center py-8 text-slate-500">
                            No matches found
                        </div>
                    ) : (
                        <div className="space-y-2 max-h-[600px] overflow-y-auto">
                            {results.results.map((result, idx) => (
                                <div
                                    key={idx}
                                    className="bg-slate-800/50 border border-slate-700 rounded-lg p-3 hover:border-indigo-500/50 transition-colors"
                                >
                                    <div className="flex items-start justify-between mb-2">
                                        <div className="flex items-center gap-2 text-sm">
                                            <span className="text-cyan-400 font-mono">{result.file}</span>
                                            <span className="text-slate-600">:</span>
                                            <span className="text-amber-400">{result.line}</span>
                                        </div>
                                        {result.symbol && (
                                            <div className="flex items-center gap-1 text-xs">
                                                <span className="bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded">
                                                    {result.symbol_type}
                                                </span>
                                                <span className="text-slate-400">{result.symbol}</span>
                                            </div>
                                        )}
                                    </div>
                                    <pre className="text-sm text-slate-300 font-mono bg-black/30 p-2 rounded overflow-x-auto">
                                        {result.content}
                                    </pre>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {!results && !loading && (
                <div className="text-center py-12 text-slate-500">
                    <p className="text-lg mb-2">🔍</p>
                    <p>Enter a search query to find code across the repository</p>
                    <p className="text-sm mt-2">Supports regex, case-sensitive search, and filtering by file/symbol type</p>
                </div>
            )}
        </div>
    );
};
