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

// Graph Types
export interface SymbolNode {
    id: string;
    name: string;
    qualified_name: string | null;
    type: 'module' | 'class' | 'function' | 'method' | 'import';
    file: string;
    start_line: number;
    end_line: number;
}

export interface GraphEdge {
    source_id: string;
    target_id: string;
    relation: 'defines' | 'calls' | 'imports';
}

export interface CyclePath {
    cycle: string[];
    type: 'import' | 'call';
}

export interface GraphResponse {
    scan_id: string;
    total_files: number;
    total_symbols: number;
    total_edges: number;
    nodes: SymbolNode[];
    edges: GraphEdge[];
    circular_dependencies: CyclePath[];
}

export type ViewMode = 'file' | 'symbol';

// Navigation
export type PageId = 'scanner' | 'metrics' | 'gateway' | 'graph';
