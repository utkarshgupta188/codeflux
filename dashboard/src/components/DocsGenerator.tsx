import React, { useState } from 'react';
import { apiService } from '../services/repoService';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { DocsScope, GenerateDocsResponse } from '../types';

interface DocsGeneratorProps {
    scanId: string;
}

export const DocsGenerator: React.FC<DocsGeneratorProps> = ({ scanId }) => {
    const [scope, setScope] = useState<DocsScope>('file');
    const [path, setPath] = useState('');
    const [symbol, setSymbol] = useState('');
    const [format, setFormat] = useState<'markdown' | 'html' | 'docstring'>('markdown');
    const [documentation, setDocumentation] = useState<string | null>(null);
    const [generatedFor, setGeneratedFor] = useState<string>('');
    const [metadata, setMetadata] = useState<GenerateDocsResponse | null>(null);
    const [showFiles, setShowFiles] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const isPathRequired = scope !== 'repo';
    const isSymbolEnabled = scope === 'file';

    const handleGenerate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (isPathRequired && !path.trim()) return;

        setLoading(true);
        setError(null);
        setDocumentation(null);
        setMetadata(null);

        try {
            const data = await apiService.generateDocs(scanId, {
                scope,
                path: isPathRequired ? path.trim() : null,
                file: isPathRequired ? path.trim() : null,
                symbol: isSymbolEnabled ? (symbol.trim() || null) : null,
                format,
            });
            setDocumentation(data.documentation);
            setGeneratedFor(data.generated_for);
            setMetadata(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Documentation generation failed');
        } finally {
            setLoading(false);
        }
    };

    const copyToClipboard = () => {
        if (documentation) {
            navigator.clipboard.writeText(documentation);
        }
    };

    return (
        <div className="bg-slate-900 text-slate-100 p-6 rounded-xl shadow-lg border border-slate-700/50">
            <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
                <span>📝</span>
                Documentation Generator
            </h2>

            {/* Generation Form */}
            <form onSubmit={handleGenerate} className="space-y-4 mb-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                            Scope
                        </label>
                        <select
                            value={scope}
                            onChange={(e) => setScope(e.target.value as DocsScope)}
                            className="w-full bg-slate-800 border-slate-700 text-slate-100 rounded-lg px-4 py-2 outline-none focus:ring-2 focus:ring-indigo-500"
                        >
                            <option value="file">File</option>
                            <option value="folder">Folder</option>
                            <option value="repo">Repo</option>
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                            {scope === 'folder' ? 'Folder Path *' : 'File Path *'}
                        </label>
                        <input
                            type="text"
                            value={path}
                            onChange={(e) => setPath(e.target.value)}
                            placeholder={scope === 'folder' ? 'e.g., app/services' : 'e.g., app/main.py'}
                            className="w-full bg-slate-800 border-slate-700 text-slate-100 rounded-lg px-4 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none disabled:opacity-60"
                            disabled={!isPathRequired}
                            required={isPathRequired}
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                            Symbol (Optional)
                        </label>
                        <input
                            type="text"
                            value={symbol}
                            onChange={(e) => setSymbol(e.target.value)}
                            placeholder="e.g., MyClass or my_function"
                            className="w-full bg-slate-800 border-slate-700 text-slate-100 rounded-lg px-4 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none disabled:opacity-60"
                            disabled={!isSymbolEnabled}
                        />
                    </div>
                </div>

                <div className="flex gap-4 items-end">
                    <div className="flex-1">
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                            Format
                        </label>
                        <select
                            value={format}
                            onChange={(e) => setFormat(e.target.value as any)}
                            className="w-full bg-slate-800 border-slate-700 text-slate-100 rounded-lg px-4 py-2 outline-none focus:ring-2 focus:ring-indigo-500"
                        >
                            <option value="markdown">Markdown</option>
                            <option value="docstring">Docstring</option>
                            <option value="html">HTML</option>
                        </select>
                    </div>

                    <button
                        type="submit"
                        disabled={loading || (isPathRequired && !path.trim())}
                        className="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors font-medium"
                    >
                        {loading ? 'Generating...' : 'Generate Docs'}
                    </button>
                </div>
            </form>

            {/* Error */}
            {error && (
                <div className="bg-red-900/20 border border-red-800 text-red-300 p-4 rounded-lg mb-4">
                    Error: {error}
                </div>
            )}

            {/* Loading */}
            {loading && (
                <div className="flex flex-col items-center justify-center p-8 space-y-4">
                    <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-400"></div>
                    <p className="text-slate-400 animate-pulse">Generating documentation...</p>
                </div>
            )}

            {/* Documentation Result */}
            {documentation && !loading && (
                <div className="space-y-4">
                    <div className="flex items-center justify-between pb-2 border-b border-slate-700">
                        <div className="text-sm text-slate-400">
                            Generated for: <span className="text-cyan-400 font-mono">{generatedFor}</span>
                        </div>
                        <button
                            onClick={copyToClipboard}
                            className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 rounded-lg text-sm transition-colors"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                            </svg>
                            Copy
                        </button>
                    </div>

                    {metadata && (
                        <div className="bg-slate-900/60 border border-slate-700 rounded-lg p-4 text-sm text-slate-300 space-y-2">
                            <div className="flex flex-wrap gap-4">
                                <div>
                                    <span className="text-slate-400">Included files:</span>{' '}
                                    <span className="text-slate-200 font-medium">{metadata.included_files.length}</span>
                                </div>
                                <div>
                                    <span className="text-slate-400">Scanned:</span>{' '}
                                    <span className="text-slate-200 font-medium">{metadata.stats.files_scanned}</span>
                                </div>
                                <div>
                                    <span className="text-slate-400">Chars:</span>{' '}
                                    <span className="text-slate-200 font-medium">{metadata.stats.total_chars}</span>
                                </div>
                            </div>

                            {metadata.truncated && (
                                <div className="text-amber-300">
                                    Output truncated due to size limits.
                                </div>
                            )}

                            {metadata.included_files.length > 0 && (
                                <button
                                    type="button"
                                    onClick={() => setShowFiles(!showFiles)}
                                    className="text-indigo-300 hover:text-indigo-200"
                                >
                                    {showFiles ? 'Hide included files' : 'Show included files'}
                                </button>
                            )}

                            {showFiles && (
                                <ul className="mt-2 max-h-40 overflow-y-auto text-xs text-slate-400 space-y-1">
                                    {metadata.included_files.map((filePath) => (
                                        <li key={filePath} className="font-mono">
                                            {filePath}
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </div>
                    )}

                    <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6 max-h-[600px] overflow-y-auto">
                        {format === 'markdown' ? (
                            <div className="prose prose-invert max-w-none">
                                <ReactMarkdown
                                    components={{
                                        code(props: any) {
                                            const { node, inline, className, children, ...rest } = props;
                                            const match = /language-(\w+)/.exec(className || '');
                                            return !inline && match ? (
                                                <SyntaxHighlighter
                                                    style={vscDarkPlus}
                                                    language={match[1]}
                                                    PreTag="div"
                                                    {...rest}
                                                >
                                                    {String(children).replace(/\n$/, '')}
                                                </SyntaxHighlighter>
                                            ) : (
                                                <code className={className} {...rest}>
                                                    {children}
                                                </code>
                                            );
                                        },
                                    }}
                                >
                                    {documentation}
                                </ReactMarkdown>
                            </div>
                        ) : format === 'html' ? (
                            <div dangerouslySetInnerHTML={{ __html: documentation }} className="prose prose-invert max-w-none" />
                        ) : (
                            <pre className="text-sm text-slate-300 font-mono whitespace-pre-wrap">
                                {documentation}
                            </pre>
                        )}
                    </div>
                </div>
            )}

            {!documentation && !loading && !error && (
                <div className="text-center py-12 text-slate-500">
                    <p className="text-lg mb-2">📝</p>
                    <p>Enter a file path to generate AI-powered documentation</p>
                    <p className="text-sm mt-2">Optionally specify a symbol (class/function) for targeted docs</p>
                </div>
            )}
        </div>
    );
};
