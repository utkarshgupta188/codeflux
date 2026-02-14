import React, { useState, useRef, useEffect } from 'react';
import { apiService } from '../services/repoService';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface Step {
    step_number: number;
    thought: string;
    tool?: string;
    tool_input?: any;
    tool_output?: string;
    is_final: boolean;
    answer?: string;
}

interface AgentResult {
    steps: Step[];
    final_answer: string;
}

interface AgentChatProps {
    repoId: string;
}

export const AgentChat: React.FC<AgentChatProps> = ({ repoId }) => {
    const [prompt, setPrompt] = useState('');
    const [result, setResult] = useState<AgentResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const bottomRef = useRef<HTMLDivElement>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!prompt.trim()) return;

        setLoading(true);
        setError(null);
        setResult(null);

        try {
            const data = await apiService.runAgent(repoId, prompt);
            setResult(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Agent run failed');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (bottomRef.current) {
            bottomRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [result, loading]);

    return (
        <div className="flex flex-col h-full bg-slate-900 text-slate-100 p-4 rounded-xl shadow-inner border border-slate-700/50">
            <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-2 scrollbar-thin scrollbar-thumb-slate-600">
                {!result && !loading && (
                    <div className="text-center text-slate-500 mt-20">
                        <h3 className="text-xl font-semibold mb-2">Autonomous Coding Agent</h3>
                        <p>Ask me to explore the codebase, find bugs, or explain complex logic.</p>
                        <p className="text-sm mt-4 italic">Example: "Find where dependency injection is used and list related files."</p>
                    </div>
                )}

                {result && (
                    <div className="space-y-6">
                        {/* Steps (Thinking Process) */}
                        <div className="space-y-4">
                            {result.steps.map((step) => (
                                <div key={step.step_number} className="bg-slate-800/50 rounded-lg p-3 border border-slate-700 text-sm">
                                    <div className="flex items-center gap-2 mb-2">
                                        <span className="bg-amber-500/10 text-amber-400 px-2 py-0.5 rounded text-xs font-mono uppercase">
                                            Step {step.step_number}
                                        </span>
                                        <span className="font-semibold text-slate-300">Thinking</span>
                                    </div>
                                    <p className="text-slate-400 mb-3 ml-1">{step.thought}</p>

                                    {step.tool && (
                                        <div className="bg-black/30 rounded border border-slate-700 overflow-hidden">
                                            <div className="bg-slate-800 px-3 py-1 flex items-center justify-between">
                                                <span className="font-mono text-cyan-400 text-xs">🛠 {step.tool}</span>
                                            </div>
                                            <div className="p-2 font-mono text-xs text-slate-300 overflow-x-auto">
                                                <div className="mb-1 text-slate-500">Input:</div>
                                                <pre>{JSON.stringify(step.tool_input, null, 2)}</pre>
                                                {step.tool_output && (
                                                    <>
                                                        <div className="mt-2 mb-1 text-slate-500 border-t border-slate-700 pt-2">Output:</div>
                                                        <div className="max-h-40 overflow-y-auto text-green-400/80">
                                                            {step.tool_output.slice(0, 500)}
                                                            {step.tool_output.length > 500 && '... (truncated)'}
                                                        </div>
                                                    </>
                                                )}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>

                        {/* Final Answer */}
                        {result.final_answer && (
                            <div className="bg-gradient-to-br from-indigo-900/30 to-purple-900/30 rounded-xl p-6 border border-indigo-500/30 shadow-lg">
                                <div className="flex items-center gap-2 mb-4">
                                    <span className="text-2xl">🤖</span>
                                    <h3 className="text-lg font-bold text-white">Agent Response</h3>
                                </div>
                                <div className="prose prose-invert max-w-none text-slate-200">
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
                                        {result.final_answer}
                                    </ReactMarkdown>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {loading && (
                    <div className="flex flex-col items-center justify-center p-8 space-y-4">
                        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-400"></div>
                        <p className="text-slate-400 animate-pulse">Analyzing codebase...</p>
                    </div>
                )}

                {error && (
                    <div className="bg-red-900/20 border border-red-800 text-red-300 p-4 rounded-lg">
                        Error: {error}
                    </div>
                )}
                <div ref={bottomRef} />
            </div>

            <form onSubmit={handleSubmit} className="relative">
                <input
                    type="text"
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="Ask the agent to investigate..."
                    className="w-full bg-slate-800 border-slate-700 text-slate-100 rounded-lg pl-4 pr-12 py-3 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none shadow-lg"
                    disabled={loading}
                />
                <button
                    type="submit"
                    disabled={loading || !prompt.trim()}
                    className="absolute right-2 top-2 p-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-md transition-colors"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-white" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                </button>
            </form>
        </div>
    );
};
