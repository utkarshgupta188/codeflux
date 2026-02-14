export type ScanStatus = 'pending' | 'scanning' | 'completed' | 'failed';

export interface RepoScanRequest {
    path: string;
    source: 'local' | 'github';
}

export interface ScanResult {
    scanId: string;
    status: ScanStatus;
    stats?: {
        files: number;
        symbols: number;
        dependencies: number;
    };
    error?: string;
}

export interface RepoHealth {
    repoId: string;
    riskScore: number;
    circularDependencies: number;
    complexityScore: number;
    hotspots: Array<{
        file: string;
        score: number;
    }>;
}

// AI Gateway Metrics Types
export type TimeRange = 'last_1h' | 'last_24h' | 'last_7d';

export interface ProviderSplit {
    provider: string;
    count: number;
    percentage: number;
}

export interface MetricsSummary {
    total_requests: number;
    avg_latency_ms: number;
    p95_latency_ms: number;
    fallback_rate_percent: number;
    provider_split: ProviderSplit[];
}

// Chat Types
export interface ChatRequest {
    prompt: string;
    preferred_model?: string;
    preferred_provider?: string;
}

export interface ChatResponse {
    response: string;
    model_used: string;
    provider_used: string;
    latency_ms: number;
}

// Navigation
export type PageId = 'scanner' | 'metrics' | 'gateway';
