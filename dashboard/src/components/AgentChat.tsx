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

interface ChatMessage {
    id: string;
    type: 'user' | 'agent';
    content: string;
    result?: AgentResult;
    timestamp: Date;
}

interface AgentChatProps {
    repoId: string;
}

export const AgentChat: React.FC<AgentChatProps> = ({ repoId }) => {
    const [prompt, setPrompt] = useState('');
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const bottomRef = useRef<HTMLDivElement>(null);
    const STORAGE_KEY = `agent_chat_${repoId}`;

    // Load history on mount
    useEffect(() => {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
            try {
                const parsed = JSON.parse(saved);
                // Hydrate dates
                const hydrated = parsed.map((m: any) => ({
                    ...m,
                    timestamp: new Date(m.timestamp)
                }));
                setMessages(hydrated);
            } catch (e) {
                console.error("Failed to load chat history", e);
            }
        }
    }, [repoId]);

    // Save history on change
    useEffect(() => {
        if (messages.length > 0) {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
        }
    }, [messages, repoId]);

    const clearHistory = () => {
        if (confirm('Are you sure you want to clear the chat history?')) {
            setMessages([]);
            localStorage.removeItem(STORAGE_KEY);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!prompt.trim()) return;

        const userMessage: ChatMessage = {
            id: Date.now().toString(),
            type: 'user',
            content: prompt.trim(),
            timestamp: new Date(),
        };

        setMessages(prev => [...prev, userMessage]);
        setPrompt(''); // Clear input immediately after sending
        setLoading(true);
        setError(null);

        try {
            const data = await apiService.runAgent(repoId, userMessage.content);
            const agentMessage: ChatMessage = {
                id: (Date.now() + 1).toString(),
                type: 'agent',
                content: data.final_answer,
                result: data,
                timestamp: new Date(),
            };
            setMessages(prev => [...prev, agentMessage]);
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
    }, [messages, loading]);

    return (
        <div className="flex flex-col h-full bg-slate-900 text-slate-100 p-4 rounded-xl shadow-inner border border-slate-700/50">
            {messages.length > 0 && (
                <div className="flex justify-end mb-2">
                    <button
                        onClick={clearHistory}
                        className="text-xs text-slate-400 hover:text-red-400 transition-colors flex items-center gap-1"
                        title="Clear conversation history"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                        Clear History
                    </button>
                </div>
            )}
            <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-2 scrollbar-thin scrollbar-thumb-slate-600">
                {messages.length === 0 && !loading && (
                    <div className="text-center text-slate-500 mt-20">
                        <h3 className="text-xl font-semibold mb-2">Autonomous Coding Agent</h3>
                        <p>Ask me to explore the codebase, find bugs, or explain complex logic.</p>
                        <p className="text-sm mt-4 italic">Example: "Find where dependency injection is used and list related files."</p>
                    </div>
                )}

                {messages.map((message) => (
                    <div key={message.id}>
                        {message.type === 'user' ? (
                            <div className="flex justify-end mb-4">
                                <div className="bg-indigo-600 rounded-lg px-4 py-2 max-w-[80%]">
                                    <p className="text-white">{message.content}</p>
                                </div>
                            </div>
                        ) : (
                            <div className="space-y-4 mb-6">
                                {/* Steps (Thinking Process) - Collapsible */}
                                {message.result && message.result.steps.length > 0 && (
                                    <details className="bg-slate-800/30 rounded-lg border border-slate-700/50">
                                        <summary className="cursor-pointer px-4 py-2 text-sm text-slate-400 hover:text-slate-300">
                                            View thinking process ({message.result.steps.length} steps)
                                        </summary>
                                        <div className="p-4 space-y-3 border-t border-slate-700/50">
                                            {message.result.steps.map((step) => (
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
                                    </details>
                                )}

                                {/* Final Answer */}
                                <div className="bg-gradient-to-br from-slate-800/50 to-slate-800/30 rounded-xl p-4 border border-slate-700/50">
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
                                            {message.content}
                                        </ReactMarkdown>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                ))}

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
