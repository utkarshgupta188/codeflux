import { useState, useEffect } from 'react';
import { RepoScanner } from './components/RepoScanner';
import { HealthDashboard } from './components/HealthDashboard';
import { MetricsDashboard } from './components/MetricsDashboard';
import { GatewayPlayground } from './components/GatewayPlayground';
import { apiService } from './services/repoService';
import type { PageId } from './types';

function App() {
  const [activePage, setActivePage] = useState<PageId>('scanner');
  const [activeRepoId, setActiveRepoId] = useState<string | null>(null);
  const [backendUp, setBackendUp] = useState<boolean | null>(null);

  // Health check on mount
  useEffect(() => {
    apiService.healthCheck().then(setBackendUp);
    const interval = setInterval(() => {
      apiService.healthCheck().then(setBackendUp);
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  const navItems: { id: PageId; label: string; icon: string }[] = [
    { id: 'scanner', label: 'Repo Scanner', icon: '🔍' },
    { id: 'metrics', label: 'Metrics', icon: '📊' },
    { id: 'gateway', label: 'AI Gateway', icon: '🤖' },
  ];

  return (
    <div className="min-h-screen bg-dark-900 flex flex-col">
      {/* Header */}
      <header className="border-b border-dark-700 bg-dark-800/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 bg-gradient-to-br from-primary-500 to-blue-700 rounded-lg flex items-center justify-center font-bold text-white text-sm shadow-lg shadow-primary-500/20">
              CF
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight text-white leading-none">CodeFlux</h1>
              <p className="text-[10px] text-gray-500 tracking-widest uppercase">AI Gateway Dashboard</p>
            </div>
          </div>

          {/* Nav Tabs */}
          <nav className="hidden sm:flex items-center gap-1 bg-dark-900/50 rounded-lg p-1 border border-dark-700">
            {navItems.map((item) => (
              <button
                key={item.id}
                onClick={() => setActivePage(item.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${activePage === item.id
                    ? 'bg-primary-600 text-white shadow-sm'
                    : 'text-gray-400 hover:text-white hover:bg-dark-700/50'
                  }`}
              >
                <span>{item.icon}</span>
                {item.label}
              </button>
            ))}
          </nav>

          {/* Status Badge */}
          <div className="flex items-center gap-1.5 text-xs text-gray-500 bg-dark-900/50 px-3 py-1.5 rounded-full border border-dark-700">
            <span className={`w-2 h-2 rounded-full ${backendUp === null ? 'bg-gray-500 animate-pulse' :
                backendUp ? 'bg-green-500 animate-pulse' : 'bg-red-500'
              }`} />
            {backendUp === null ? 'Checking…' : backendUp ? 'Connected' : 'Offline'}
          </div>
        </div>

        {/* Mobile Nav */}
        <div className="sm:hidden flex border-t border-dark-700">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setActivePage(item.id)}
              className={`flex-1 py-2.5 text-center text-xs font-medium transition-all ${activePage === item.id
                  ? 'text-primary-400 border-b-2 border-primary-500 bg-primary-500/5'
                  : 'text-gray-500'
                }`}
            >
              <span className="block text-base mb-0.5">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-8">
        {/* Repo Scanner Page */}
        {activePage === 'scanner' && (
          <div className="space-y-8">
            <div className="text-center mb-2">
              <h2 className="text-2xl font-bold text-white mb-1">Repository Health Analysis</h2>
              <p className="text-gray-500 text-sm">Scan any codebase for complexity, dependencies, and hotspots</p>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 max-w-2xl mx-auto">
              <FeatureCard icon="📊" title="Static Analysis" desc="Symbols & LOC" />
              <FeatureCard icon="📦" title="Dependency Scan" desc="npm & pip" />
              <FeatureCard icon="🔥" title="Hotspot Detection" desc="Complexity scoring" />
              <FeatureCard icon="🩺" title="Health Score" desc="Risk assessment" />
            </div>

            <RepoScanner onScanComplete={setActiveRepoId} />

            {activeRepoId && (
              <div>
                <div className="flex items-center gap-3 mb-6">
                  <div className="h-px flex-1 bg-dark-700" />
                  <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Analysis Results</h2>
                  <div className="h-px flex-1 bg-dark-700" />
                </div>
                <HealthDashboard repoId={activeRepoId} />
              </div>
            )}
          </div>
        )}

        {/* Metrics Page */}
        {activePage === 'metrics' && <MetricsDashboard />}

        {/* Gateway Playground Page */}
        {activePage === 'gateway' && <GatewayPlayground />}
      </main>

      {/* Footer */}
      <footer className="border-t border-dark-700 py-4 mt-auto">
        <div className="max-w-6xl mx-auto px-6 flex items-center justify-between text-xs text-gray-600">
          <span>CodeFlux © 2026</span>
          <span className="hidden sm:inline">React + Vite + TailwindCSS + FastAPI</span>
          <span className="font-mono text-gray-700">v1.0.0</span>
        </div>
      </footer>
    </div>
  );
}

const FeatureCard = ({ icon, title, desc }: { icon: string; title: string; desc: string }) => (
  <div className="bg-dark-800/50 border border-dark-700 rounded-lg p-3 text-center hover:border-primary-500/30 transition-colors group">
    <div className="text-xl mb-1 group-hover:scale-110 transition-transform inline-block">{icon}</div>
    <div className="text-xs font-semibold text-gray-300">{title}</div>
    <div className="text-[10px] text-gray-600">{desc}</div>
  </div>
);

export default App;
