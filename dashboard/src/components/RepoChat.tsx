/**
 * RepoChat — AI-powered repository Q&A panel.
 * Sends questions to POST /repo/{id}/ask with structural context.
 */

import { useState, useRef, useEffect } from 'react';
import { apiService } from '../services/repoService';

interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
    provider?: string;
    latency?: number;
}

interface RepoChatProps {
    scanId: string;
}

export function RepoChat({ scanId }: RepoChatProps) {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);
    const STORAGE_KEY = `repo_chat_${scanId}`;

    useEffect(() => {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
            try {
                const parsed = JSON.parse(saved);
                setMessages(parsed);
            } catch (e) {
                console.error('Failed to load repo chat history', e);
            }
        }
    }, [scanId]);

    useEffect(() => {
        if (messages.length > 0) {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
        }
    }, [messages, scanId]);

    const clearHistory = () => {
        if (confirm('Are you sure you want to clear the repo chat history?')) {
            setMessages([]);
            localStorage.removeItem(STORAGE_KEY);
        }
    };

    // Auto-scroll on new messages
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const suggestedQuestions = [
        'What are the most complex files?',
        'Are there any circular dependencies?',
        'Which symbols have the most connections?',
        'Summarize the architecture of this repo.',
        'What are the main architectural risks?',
    ];

    const handleSubmit = async (question?: string) => {
        const q = question || input.trim();
        if (!q || loading) return;

        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: q }]);
        setLoading(true);

        try {
            const answer = await apiService.askRepo(scanId, q);
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: answer.answer,
                provider: answer.provider_used,
                latency: answer.latency_ms,
            }]);
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Failed to get response';
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: `⚠️ ${message}`,
            }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{
            background: '#0f172a',
            border: '1px solid #1e293b',
            borderRadius: 12,
            display: 'flex',
            flexDirection: 'column',
            height: 520,
            overflow: 'hidden',
        }}>
            {/* Header */}
            <div style={{
                padding: '12px 16px',
                borderBottom: '1px solid #1e293b',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
            }}>
                <span style={{ fontSize: 16 }}>🧠</span>
                <span style={{ color: '#e2e8f0', fontWeight: 600, fontSize: 13 }}>Ask AI about this repository</span>
                {messages.length > 0 && (
                    <button
                        onClick={clearHistory}
                        style={{
                            marginLeft: 'auto',
                            fontSize: 10,
                            color: '#94a3b8',
                            background: 'transparent',
                            border: 'none',
                            cursor: 'pointer',
                        }}
                        title="Clear chat history"
                    >
                        Clear History
                    </button>
                )}
                <span style={{
                    fontSize: 10,
                    color: '#475569',
                    background: '#1e293b',
                    padding: '2px 8px',
                    borderRadius: 4,
                    fontFamily: "'JetBrains Mono', monospace",
                }}>
                    context-aware
                </span>
            </div>

            {/* Messages */}
            <div
                ref={scrollRef}
                style={{
                    flex: 1,
                    overflowY: 'auto',
                    padding: 16,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 12,
                }}
            >
                {messages.length === 0 && (
                    <div style={{ textAlign: 'center', paddingTop: 30 }}>
                        <p style={{ color: '#475569', fontSize: 12, marginBottom: 16 }}>
                            Ask questions about the repository structure, complexity, and architecture.
                        </p>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, justifyContent: 'center' }}>
                            {suggestedQuestions.map((q, i) => (
                                <button
                                    key={i}
                                    onClick={() => handleSubmit(q)}
                                    style={{
                                        background: '#1e293b',
                                        border: '1px solid #334155',
                                        borderRadius: 8,
                                        padding: '6px 12px',
                                        color: '#94a3b8',
                                        fontSize: 11,
                                        cursor: 'pointer',
                                        transition: 'all 0.15s',
                                    }}
                                    onMouseEnter={(e) => {
                                        e.currentTarget.style.borderColor = '#3b82f6';
                                        e.currentTarget.style.color = '#e2e8f0';
                                    }}
                                    onMouseLeave={(e) => {
                                        e.currentTarget.style.borderColor = '#334155';
                                        e.currentTarget.style.color = '#94a3b8';
                                    }}
                                >
                                    {q}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {messages.map((msg, i) => (
                    <div
                        key={i}
                        style={{
                            display: 'flex',
                            justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                        }}
                    >
                        <div style={{
                            maxWidth: '85%',
                            padding: '10px 14px',
                            borderRadius: msg.role === 'user' ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
                            background: msg.role === 'user' ? '#1d4ed8' : '#1e293b',
                            border: msg.role === 'user' ? 'none' : '1px solid #334155',
                            color: '#e2e8f0',
                            fontSize: 12.5,
                            lineHeight: 1.6,
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-word',
                        }}>
                            {msg.content}

                            {msg.role === 'assistant' && msg.provider && (
                                <div style={{
                                    marginTop: 8,
                                    paddingTop: 6,
                                    borderTop: '1px solid #334155',
                                    fontSize: 10,
                                    color: '#475569',
                                    display: 'flex',
                                    gap: 10,
                                }}>
                                    <span>⚡ {msg.provider}</span>
                                    {msg.latency && <span>{Math.round(msg.latency)}ms</span>}
                                </div>
                            )}
                        </div>
                    </div>
                ))}

                {loading && (
                    <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                        <div style={{
                            background: '#1e293b',
                            border: '1px solid #334155',
                            borderRadius: '12px 12px 12px 2px',
                            padding: '12px 16px',
                            color: '#475569',
                            fontSize: 12,
                            display: 'flex',
                            alignItems: 'center',
                            gap: 8,
                        }}>
                            <div style={{
                                width: 12,
                                height: 12,
                                border: '2px solid #334155',
                                borderTopColor: '#3b82f6',
                                borderRadius: '50%',
                                animation: 'spin 0.8s linear infinite',
                            }} />
                            Analyzing with graph context…
                        </div>
                    </div>
                )}
            </div>

            {/* Input */}
            <div style={{
                padding: '12px 16px',
                borderTop: '1px solid #1e293b',
                display: 'flex',
                gap: 8,
            }}>
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
                    placeholder="Ask about structure, complexity, dependencies…"
                    disabled={loading}
                    style={{
                        flex: 1,
                        background: '#1e293b',
                        border: '1px solid #334155',
                        borderRadius: 8,
                        padding: '8px 12px',
                        color: '#e2e8f0',
                        fontSize: 12,
                        outline: 'none',
                        fontFamily: "'Inter', system-ui, sans-serif",
                    }}
                />
                <button
                    onClick={() => handleSubmit()}
                    disabled={loading || !input.trim()}
                    style={{
                        background: loading || !input.trim() ? '#1e293b' : '#2563eb',
                        border: 'none',
                        borderRadius: 8,
                        padding: '8px 16px',
                        color: loading || !input.trim() ? '#475569' : '#fff',
                        fontSize: 12,
                        fontWeight: 600,
                        cursor: loading || !input.trim() ? 'default' : 'pointer',
                        transition: 'all 0.15s',
                    }}
                >
                    Ask
                </button>
            </div>
        </div>
    );
}
