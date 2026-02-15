import { useState, useEffect } from 'react';
import { RepoScanner } from './components/RepoScanner';
import { HealthDashboard } from './components/HealthDashboard';
import { GraphViewer } from './components/GraphViewer';
import { RepoChat } from './components/RepoChat';
import { AgentChat } from './components/AgentChat';
import { ImpactSimulator } from './components/ImpactSimulator';
import { CodeSearch } from './components/CodeSearch';
import { DocsGenerator } from './components/DocsGenerator';
import { DiffViewer } from './components/DiffViewer';
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
    { id: 'tools', label: 'Dev Tools', icon: '🛠️' },
    { id: 'graph', label: 'Code Graph', icon: '🧠' },
    { id: 'agent', label: 'AI Agent', icon: '🤖' },
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
              <p className="text-[10px] text-gray-500 tracking-widest uppercase">Code Analysis Platform</p>
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
      <main className={`flex-1 mx-auto w-full px-6 py-8 ${activePage === 'graph' ? 'max-w-[1400px]' : 'max-w-6xl'}`}>
        {/* Repo Scanner Page */}
        <div className={activePage === 'scanner' ? 'space-y-8' : 'hidden'}>
            <div className="text-center mb-2">
              <h2 className="text-2xl font-bold text-white mb-1">Repository Analysis</h2>
              <p className="text-gray-500 text-sm">Scan your codebase for complexity, dependencies, and structure</p>
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

        {/* Agent Page */}
        <div className={activePage === 'agent' ? 'h-[calc(100vh-8rem)]' : 'hidden'}>
            <h2 className="text-2xl font-bold text-white mb-4 text-center">AI Code Agent</h2>
            {activeRepoId ? (
              <AgentChat repoId={activeRepoId} />
            ) : (
              <div className="text-center py-16 bg-dark-800/50 rounded-xl border border-dark-700">
                <p className="text-gray-500 text-sm">Scan a repository first to use the agent.</p>
                <button
                  onClick={() => setActivePage('scanner')}
                  className="mt-3 px-4 py-2 bg-primary-600 text-white text-xs rounded-lg hover:bg-primary-500 transition-colors"
                >
                  Go to Scanner →
                </button>
              </div>
            )}
        </div>

        {/* Code Search Page */}
        <div className={activePage === 'search' ? '' : 'hidden'}>
            {activeRepoId ? (
              <CodeSearch scanId={activeRepoId} />
            ) : (
              <div className="text-center py-16 bg-dark-800/50 rounded-xl border border-dark-700">
                <p className="text-gray-500 text-sm">Scan a repository first to search code.</p>
                <button
                  onClick={() => setActivePage('scanner')}
                  className="mt-3 px-4 py-2 bg-primary-600 text-white text-xs rounded-lg hover:bg-primary-500 transition-colors"
                >
                  Go to Scanner →
                </button>
              </div>
            )}
        </div>

        {/* Dev Tools Page */}
        <div className={activePage === 'tools' ? '' : 'hidden'}>
            {activeRepoId ? (
              <div className="space-y-6">
                <CodeSearch scanId={activeRepoId} />
                <DocsGenerator scanId={activeRepoId} />
                <DiffViewer scanId={activeRepoId} />
              </div>
            ) : (
              <div className="text-center py-16 bg-dark-800/50 rounded-xl border border-dark-700">
                <p className="text-gray-500 text-sm">Scan a repository first to use developer tools.</p>
                <button
                  onClick={() => setActivePage('scanner')}
                  className="mt-3 px-4 py-2 bg-primary-600 text-white text-xs rounded-lg hover:bg-primary-500 transition-colors"
                >
                  Go to Scanner →
                </button>
              </div>
            )}
        </div>

        {/* Graph Visualization Page */}
        <div className={activePage === 'graph' ? 'space-y-4' : 'hidden'}>
            <div className="text-center mb-2">
              <h2 className="text-2xl font-bold text-white mb-1">Code Graph & Analysis</h2>
              <p className="text-gray-500 text-sm">Visualize code structure and simulate change impact</p>
            </div>
            {activeRepoId ? (
              <>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                  <GraphViewer scanId={activeRepoId} />
                  <RepoChat scanId={activeRepoId} />
                </div>
                <ImpactSimulator scanId={activeRepoId} />
              </>
            ) : (
              <div className="text-center py-16 bg-dark-800/50 rounded-xl border border-dark-700">
                <p className="text-gray-500 text-sm">Scan a repository first to visualize its code graph.</p>
                <button
                  onClick={() => setActivePage('scanner')}
                  className="mt-3 px-4 py-2 bg-primary-600 text-white text-xs rounded-lg hover:bg-primary-500 transition-colors"
                >
                  Go to Scanner →
                </button>
              </div>
            )}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-dark-700 py-4 mt-auto">
        <div className="max-w-6xl mx-auto px-6 flex items-center justify-between text-xs text-gray-600">
          <span>CodeFlux © 2026</span>
          <span className="hidden sm:inline">AI-Powered Code Analysis Platform</span>
          <span className="font-mono text-gray-700">v1.0.0</span>
        </div>
      </footer>
    </div>
  );
}

export default App;
