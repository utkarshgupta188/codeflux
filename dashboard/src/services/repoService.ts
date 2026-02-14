import type { RepoScanRequest, ScanResult, RepoHealth, MetricsSummary, TimeRange, ChatRequest, ChatResponse } from '../types';

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
}

export const apiService = new ApiService();

// Legacy export for backward compatibility
export const repoService = apiService;
