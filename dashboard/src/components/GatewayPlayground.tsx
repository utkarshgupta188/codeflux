import React, { useState } from 'react';
import { apiService } from '../services/repoService';
import type { ChatResponse } from '../types';

export const GatewayPlayground: React.FC = () => {
    const [prompt, setPrompt] = useState('');
    const [model, setModel] = useState('');
    const [provider, setProvider] = useState('');
    const [response, setResponse] = useState<ChatResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const sendRequest = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!prompt.trim()) return;

        setLoading(true);
        setError(null);
        setResponse(null);

        try {
            const result = await apiService.sendChat({
                prompt,
                ...(model && { preferred_model: model }),
                ...(provider && { preferred_provider: provider }),
            });
            setResponse(result);
        } catch (err: any) {
            setError(err.message || 'Request failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-3xl mx-auto space-y-6">
            {/* Input Card */}
            <div className="card relative overflow-hidden">
                <div className="absolute -top-20 -left-20 w-40 h-40 bg-purple-600/5 rounded-full blur-3xl pointer-events-none" />

                <div className="flex items-center gap-3 mb-5 border-b border-dark-700 pb-4">
                    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-indigo-700 flex items-center justify-center">
                        <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                        </svg>
                    </div>
                    <div>
                        <h2 className="text-xl font-bold text-white">AI Gateway Playground</h2>
                        <p className="text-xs text-gray-500">Test the routing gateway with live requests</p>
                    </div>
                </div>

                <form onSubmit={sendRequest} className="space-y-4">
                    <div>
                        <label className="text-xs text-gray-500 uppercase tracking-wider block mb-1.5">Prompt</label>
                        <textarea
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                            placeholder="Ask the AI anything..."
                            className="input w-full h-28 resize-none py-3"
                            required
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="text-xs text-gray-500 uppercase tracking-wider block mb-1.5">Provider (optional)</label>
                            <select
                                value={provider}
                                onChange={(e) => setProvider(e.target.value)}
                                className="input w-full py-2.5"
                            >
                                <option value="">Auto-route</option>
                                <option value="groq">Groq</option>
                                <option value="openrouter">OpenRouter</option>
                            </select>
                        </div>
                        <div>
                            <label className="text-xs text-gray-500 uppercase tracking-wider block mb-1.5">Model (optional)</label>
                            <input
                                type="text"
                                value={model}
                                onChange={(e) => setModel(e.target.value)}
                                placeholder="e.g. llama-3.3-70b-versatile"
                                className="input w-full py-2.5"
                            />
                        </div>
                    </div>

                    <button
                        type="submit"
                        disabled={!prompt.trim() || loading}
                        className="btn w-full py-3 font-semibold"
                    >
                        {loading ? (
                            <span className="flex items-center justify-center gap-2">
                                <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                </svg>
                                Routing…
                            </span>
                        ) : (
                            'Send Request'
                        )}
                    </button>
                </form>
            </div>

            {/* Error */}
            {error && (
                <div className="p-3 bg-red-900/30 text-red-300 rounded-lg border border-red-800/50 text-sm flex items-center gap-2">
                    <span>⚠️</span> {error}
                </div>
            )}

            {/* Response Card */}
            {response && (
                <div className="card space-y-4">
                    <div className="flex items-center justify-between border-b border-dark-700 pb-3">
                        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Response</h3>
                        <div className="flex items-center gap-3 text-xs">
                            <span className="bg-dark-900 px-2 py-1 rounded border border-dark-700 text-gray-400">
                                {response.provider_used}
                            </span>
                            <span className="bg-dark-900 px-2 py-1 rounded border border-dark-700 text-gray-400 font-mono">
                                {response.model_used}
                            </span>
                            <span className="bg-dark-900 px-2 py-1 rounded border border-dark-700 text-yellow-400 font-mono">
                                {response.latency_ms}ms
                            </span>
                        </div>
                    </div>

                    <div className="text-gray-300 text-sm leading-relaxed whitespace-pre-wrap font-mono bg-dark-900/50 p-4 rounded-lg border border-dark-700 max-h-96 overflow-y-auto">
                        {response.response}
                    </div>
                </div>
            )}
        </div>
    );
};
