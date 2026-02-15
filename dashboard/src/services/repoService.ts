import type { RepoScanRequest, ScanResult, RepoHealth, MetricsSummary, TimeRange, ChatRequest, ChatResponse, GraphResponse, RepoAnswer, SimulateChangeResponse, CostMetricsResponse, GenerateDocsRequest, GenerateDocsResponse } from '../types';

const API_BASE = 'http://localhost:8000';

class ApiService {
    // ─── Repository Scanner ─────────────────────────────────
    async scanRepo(data: RepoScanRequest): Promise<ScanResult> {
        const response = await fetch(`${API_BASE}/repo/scan`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (!response.ok) throw new Error('Failed to initiate scan');
        return response.json();
    }

    async getScanStatus(scanId: string): Promise<ScanResult> {
        const response = await fetch(`${API_BASE}/repo/${scanId}/status`);
        if (!response.ok) throw new Error('Failed to fetch status');
        return response.json();
    }

    async getRepoHealth(repoId: string): Promise<RepoHealth> {
        const response = await fetch(`${API_BASE}/repo/${repoId}/health`);
        if (!response.ok) throw new Error('Failed to fetch health metrics');
        return response.json();
    }

    // ─── AI Gateway Metrics ─────────────────────────────────
    async getMetrics(range: TimeRange = 'last_24h'): Promise<MetricsSummary> {
        const response = await fetch(`${API_BASE}/metrics/summary?range=${range}`);
        if (!response.ok) throw new Error('Failed to fetch metrics');
        return response.json();
    }

    // ─── AI Gateway Chat ────────────────────────────────────
    async sendChat(data: ChatRequest): Promise<ChatResponse> {
        const response = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            const err = await response.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(err.detail || 'Chat request failed');
        }
        return response.json();
    }

    // ─── Health Check ───────────────────────────────────────
    async healthCheck(): Promise<boolean> {
        try {
            const response = await fetch(`${API_BASE}/health`);
            return response.ok;
        } catch {
            return false;
        }
    }

    // ─── Structural Graph ────────────────────────────────────
    async getGraph(scanId: string): Promise<GraphResponse> {
        const response = await fetch(`${API_BASE}/repo/${scanId}/graph`);
        if (!response.ok) throw new Error('Failed to fetch graph');
        return response.json();
    }

    // ─── AI Repo Q&A ─────────────────────────────────────────
    async askRepo(scanId: string, question: string): Promise<RepoAnswer> {
        const response = await fetch(`${API_BASE}/repo/${scanId}/ask`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question }),
        });
        if (!response.ok) {
            const err = await response.json().catch(() => ({ detail: 'Ask failed' }));
            throw new Error(err.detail || 'Failed to get answer');
        }
        return response.json();
    }

    // ─── Impact Simulation ───────────────────────────────────
    async simulateChange(scanId: string, file?: string, symbol?: string, depthLimit?: number): Promise<SimulateChangeResponse> {
        const response = await fetch(`${API_BASE}/repo/${scanId}/simulate-change`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ file, symbol, depth_limit: depthLimit ?? 5 }),
        });
        if (!response.ok) {
            const err = await response.json().catch(() => ({ detail: 'Simulation failed' }));
            throw new Error(err.detail || 'Failed to simulate change');
        }
        return response.json();
    }

    // ─── Cost Metrics ────────────────────────────────────────
    async getCostMetrics(): Promise<CostMetricsResponse> {
        const response = await fetch(`${API_BASE}/metrics/cost`);
        if (!response.ok) throw new Error('Failed to fetch cost metrics');
        return response.json();
    }

    async getVersions(repoId: string): Promise<any[]> {
        const response = await fetch(`${API_BASE}/repo/${repoId}/versions`);
        if (!response.ok) throw new Error('Failed to fetch versions');
        return response.json();
    }

    async getDiff(repoId: string, base: string, head: string): Promise<any> {
        const response = await fetch(`${API_BASE}/repo/diff`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ base_scan_id: base, head_scan_id: head })
        });
        if (!response.ok) throw new Error('Failed to fetch diff');
        return response.json();
    }

    async runAgent(repoId: string, prompt: string): Promise<any> {
        const response = await fetch(`${API_BASE}/agent/run`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ repo_id: repoId, prompt })
        });
        if (!response.ok) throw new Error('Agent run failed');
        return response.json();
    }

    // ─── Code Search ─────────────────────────────────────────
    async searchCode(scanId: string, searchParams: {
        query: string;
        file_type?: string | null;
        symbol_type?: string | null;
        case_sensitive?: boolean;
        regex?: boolean;
        limit?: number;
    }): Promise<any> {
        const response = await fetch(`${API_BASE}/repo/${scanId}/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(searchParams)
        });
        if (!response.ok) throw new Error('Search failed');
        return response.json();
    }

    // ─── Documentation Generator ─────────────────────────────
    async generateDocs(scanId: string, params: GenerateDocsRequest): Promise<GenerateDocsResponse> {
        const response = await fetch(`${API_BASE}/repo/${scanId}/generate-docs`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });
        if (!response.ok) throw new Error('Documentation generation failed');
        return response.json();
    }
}

export const apiService = new ApiService();

// Legacy export for backward compatibility
export const repoService = apiService;
