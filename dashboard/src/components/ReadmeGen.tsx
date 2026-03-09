import React, { useState } from 'react';
import { FileText, Sparkles, Copy, Check, Loader2, AlertCircle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { repoService } from '../services/repoService';

interface ReadmeGenProps {
    scanId: string | null;
}

export const ReadmeGen: React.FC<ReadmeGenProps> = ({ scanId }) => {
    const [loading, setLoading] = useState(false);
    const [readme, setReadme] = useState<string | null>(null);
    const [copied, setCopied] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const generateReadme = async () => {
        if (!scanId) {
            setError('Please scan a repository first in the Repo Scanner.');
            return;
        }

        setLoading(true);
        setError(null);
        try {
            const response = await repoService.generateReadme(scanId);
            setReadme(response.content);
        } catch (err) {
            console.error('README generation failed:', err);
            setError('Failed to generate README. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const copyToClipboard = () => {
        if (readme) {
            navigator.clipboard.writeText(readme);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    return (
        <div className="space-y-6 max-w-5xl mx-auto py-8 px-4">
            <div className="text-center space-y-2 mb-10">
                <h2 className="text-3xl font-bold text-white flex items-center justify-center gap-3">
                    <Sparkles className="h-8 w-8 text-blue-500" />
                    Professional README Generator
                </h2>
                <p className="text-gray-400 max-w-2xl mx-auto">
                    Generate beautiful, high-quality README.md files for your projects using advanced AI analysis.
                </p>
            </div>

            {!readme ? (
                <div className="bg-gray-900/50 rounded-2xl border border-white/5 p-12 text-center backdrop-blur-sm">
                    <div className="bg-blue-500/10 w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6 border border-blue-500/20">
                        <FileText className="h-10 w-10 text-blue-500" />
                    </div>

                    <h3 className="text-xl font-semibold text-white mb-3">Ready to transform your repository?</h3>
                    <p className="text-gray-400 mb-8 max-w-md mx-auto">
                        Our AI Agent will analyze your code, dependencies, and structure to create a professional README formatted for GitHub.
                    </p>

                    {!scanId && (
                        <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 flex items-center gap-3 text-amber-500 max-w-lg mx-auto mb-8">
                            <AlertCircle className="h-5 w-5 flex-shrink-0" />
                            <p className="text-sm text-left">No repository scan found. Go to the <strong>Repo Scanner</strong> first to analyze your project.</p>
                        </div>
                    )}

                    <button
                        onClick={generateReadme}
                        disabled={loading || !scanId}
                        className={`
              inline-flex items-center space-x-2 px-8 py-4 rounded-xl font-semibold transition-all duration-300
              ${loading
                                ? 'bg-blue-600/50 cursor-not-allowed text-white/50'
                                : scanId
                                    ? 'bg-blue-600 hover:bg-blue-500 text-white shadow-xl shadow-blue-500/20 hover:scale-105'
                                    : 'bg-gray-800 text-gray-500 cursor-not-allowed opacity-50'
                            }
            `}
                    >
                        {loading ? (
                            <>
                                <Loader2 className="h-5 w-5 animate-spin" />
                                <span>Analyzing Base...</span>
                            </>
                        ) : (
                            <>
                                <Sparkles className="h-5 w-5" />
                                <span>Generate Professional README</span>
                            </>
                        )}
                    </button>

                    {error && (
                        <p className="text-red-400 mt-6 flex items-center justify-center gap-2">
                            <AlertCircle className="h-4 w-4" />
                            {error}
                        </p>
                    )}
                </div>
            ) : (
                <div className="bg-gray-900/50 rounded-2xl border border-white/5 overflow-hidden backdrop-blur-sm animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <div className="flex items-center justify-between px-6 py-4 border-b border-white/5 bg-gray-900/80">
                        <div className="flex items-center space-x-3">
                            <FileText className="h-5 w-5 text-blue-500" />
                            <h3 className="text-lg font-medium text-white">Generated README.md</h3>
                        </div>

                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => setReadme(null)}
                                className="text-xs text-gray-500 hover:text-white px-3 py-1 transparent"
                            >
                                Regenerate
                            </button>
                            <button
                                onClick={copyToClipboard}
                                className={`
                  flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200
                  ${copied
                                        ? 'bg-green-500 text-white'
                                        : 'bg-white/5 hover:bg-white/10 text-gray-300 hover:text-white border border-white/10'}
                `}
                            >
                                {copied ? (
                                    <>
                                        <Check className="h-4 w-4" />
                                        <span>Copied!</span>
                                    </>
                                ) : (
                                    <>
                                        <Copy className="h-4 w-4" />
                                        <span>Copy Markdown</span>
                                    </>
                                )}
                            </button>
                        </div>
                    </div>

                    <div className="p-8 prose prose-invert prose-blue max-w-none overflow-auto max-h-[70vh]">
                        <ReactMarkdown
                            components={{
                                code({ node, inline, className, children, ...props }: any) {
                                    const match = /language-(\w+)/.exec(className || '');
                                    return !inline && match ? (
                                        <div className="relative group">
                                            <pre className={`${className} bg-gray-950/50 p-4 rounded-xl border border-white/5 overflow-x-auto`} {...props}>
                                                <code>{children}</code>
                                            </pre>
                                        </div>
                                    ) : (
                                        <code className="bg-white/10 px-1.5 py-0.5 rounded text-blue-400" {...props}>
                                            {children}
                                        </code>
                                    );
                                },
                                h1: ({ children }) => <h1 className="text-3xl font-bold text-white mb-6 pb-2 border-b border-white/10">{children}</h1>,
                                h2: ({ children }) => <h2 className="text-2xl font-bold text-white mt-10 mb-4 flex items-center gap-2">{children}</h2>,
                                h3: ({ children }) => <h3 className="text-xl font-semibold text-white mt-8 mb-3">{children}</h3>,
                                p: ({ children }) => <p className="text-gray-300 leading-relaxed mb-4">{children}</p>,
                                ul: ({ children }) => <ul className="space-y-2 mb-6 ml-4 list-disc marker:text-blue-500">{children}</ul>,
                                ol: ({ children }) => <ol className="space-y-2 mb-6 ml-4 list-decimal marker:text-blue-500">{children}</ol>,
                                li: ({ children }) => <li className="text-gray-300">{children}</li>,
                                table: ({ children }) => (
                                    <div className="overflow-x-auto my-8">
                                        <table className="w-full border-collapse border border-white/10 rounded-xl overflow-hidden">{children}</table>
                                    </div>
                                ),
                                thead: ({ children }) => <thead className="bg-white/5">{children}</thead>,
                                th: ({ children }) => <th className="px-4 py-3 text-left text-sm font-semibold text-white border border-white/10">{children}</th>,
                                td: ({ children }) => <td className="px-4 py-3 text-sm text-gray-300 border border-white/10">{children}</td>,
                                blockquote: ({ children }) => <blockquote className="border-l-4 border-blue-500/50 pl-4 py-2 my-6 italic text-gray-400 bg-blue-500/5">{children}</blockquote>
                            }}
                        >
                            {readme}
                        </ReactMarkdown>
                    </div>
                </div>
            )}
        </div>
    );
};
