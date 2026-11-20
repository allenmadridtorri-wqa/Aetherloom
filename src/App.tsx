import React, { useCallback, useEffect, useState } from 'react';
import {
  Terminal,
  Shield,
  Database,
  Layers,
  FolderCode,
  Menu,
  X,
} from 'lucide-react';
import { OrchestratorView } from './components/OrchestratorView';
import { SafetyOpsView } from './components/SafetyOpsView';
import { MemoryDreamSkillsView } from './components/MemoryDreamSkillsView';
import { AdaptersVerifyView } from './components/AdaptersVerifyView';
import { SourceTreeView } from './components/SourceTreeView';
import type {
  AcceptanceReport,
  NavTab,
  OrchestrationResult,
  PluginFileEntry,
  WorkbenchState,
} from './types';

const NAV_ITEMS: Array<{ id: NavTab; label: string; icon: React.ComponentType<{ className?: string }> }> = [
  { id: 'orchestrator', label: 'Orchestrator', icon: Terminal },
  { id: 'safety', label: 'Warden and Ops', icon: Shield },
  { id: 'memory', label: 'Memory and Dream', icon: Database },
  { id: 'adapters', label: 'Adapters and Tests', icon: Layers },
  { id: 'source', label: 'Source Tree', icon: FolderCode },
];

const TAB_TITLES: Record<NavTab, string> = {
  orchestrator: 'AetherLoom / Orchestrator (/supergravity)',
  safety: 'AetherLoom / Warden and N.A.T.A.L.I.E. Operations',
  memory: 'AetherLoom / SQLite FTS5, Dream, and Skill Learning',
  adapters: 'AetherLoom / Host Adapters and Acceptance Tests',
  source: 'AetherLoom / Complete Plugin Source Tree',
};

export default function App() {
  const [activeTab, setActiveTab] = useState<NavTab>('orchestrator');
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [state, setState] = useState<WorkbenchState | null>(null);
  const [files, setFiles] = useState<PluginFileEntry[]>([]);
  const [lastRun, setLastRun] = useState<OrchestrationResult | null>(null);
  const [acceptanceReport, setAcceptanceReport] = useState<AcceptanceReport | null>(null);
  const [runningAcceptance, setRunningAcceptance] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const loadState = useCallback(async () => {
    const resp = await fetch('/api/state');
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || 'Failed to load AetherLoom runtime state.');
    setState(data as WorkbenchState);
  }, []);

  const loadTree = useCallback(async () => {
    const resp = await fetch('/api/tree');
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || 'Failed to load plugin source tree.');
    setFiles((data.files || []) as PluginFileEntry[]);
  }, []);

  useEffect(() => {
    let active = true;
    Promise.all([loadState(), loadTree()])
      .catch((err) => {
        if (active) setLoadError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [loadState, loadTree]);

  const handleRunAcceptance = useCallback(async () => {
    setRunningAcceptance(true);
    try {
      const resp = await fetch('/api/acceptance/run', { method: 'POST' });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || 'Acceptance test run failed.');
      setAcceptanceReport(data as AcceptanceReport);
      setActiveTab('adapters');
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : String(err));
    } finally {
      setRunningAcceptance(false);
    }
  }, []);

  const handleRebuildAdapters = useCallback(async () => {
    const resp = await fetch('/api/adapters/rebuild', { method: 'POST' });
    if (!resp.ok) {
      const data = await resp.json();
      throw new Error(data.error || 'Adapter rebuild failed.');
    }
    await loadTree();
  }, [loadTree]);

  function selectTab(tab: NavTab) {
    setActiveTab(tab);
    setMobileNavOpen(false);
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex">
      {/* Desktop Sidebar (248px) */}
      <aside className="hidden lg:flex lg:flex-col lg:w-64 lg:shrink-0 bg-white border-r border-slate-200">
        <div className="h-16 px-6 flex items-center border-b border-slate-200">
          <span className="text-lg font-bold tracking-tight text-slate-900 font-display whitespace-nowrap">
            AetherLoom
          </span>
        </div>

        <nav aria-label="Primary sections" className="flex-1 p-3 space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = activeTab === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => selectTab(item.id)}
                aria-current={active ? 'page' : undefined}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 min-h-[42px] text-sm font-medium rounded-md transition-colors whitespace-nowrap cursor-pointer ${
                  active
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                }`}
              >
                <Icon className="w-4 h-4 shrink-0" aria-hidden="true" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="p-5 border-t border-slate-200 text-xs text-slate-500 space-y-1.5">
          <div className="font-mono text-slate-700">/supergravity · 18 agents</div>
          <div>Free-tier aware · SQLite FTS5</div>
          <div>{files.length} plugin files generated</div>
        </div>
      </aside>

      {/* Mobile Drawer */}
      {mobileNavOpen && (
        <div className="fixed inset-0 z-40 lg:hidden flex">
          <div
            className="fixed inset-0 bg-slate-900/40"
            onClick={() => setMobileNavOpen(false)}
            aria-hidden="true"
          />
          <aside className="relative z-50 w-64 max-w-[80vw] bg-white border-r border-slate-200 flex flex-col">
            <div className="h-14 px-4 flex items-center justify-between border-b border-slate-200">
              <span className="text-base font-bold font-display text-slate-900">AetherLoom</span>
              <button
                type="button"
                onClick={() => setMobileNavOpen(false)}
                aria-label="Close navigation menu"
                className="p-2 text-slate-600 hover:text-slate-900 cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <nav aria-label="Mobile sections" className="p-3 space-y-1">
              {NAV_ITEMS.map((item) => {
                const Icon = item.icon;
                const active = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => selectTab(item.id)}
                    className={`w-full flex items-center gap-3 px-3.5 py-2.5 min-h-[44px] text-sm font-medium rounded-md whitespace-nowrap cursor-pointer ${
                      active
                        ? 'bg-blue-50 text-blue-700'
                        : 'text-slate-700 hover:bg-slate-100'
                    }`}
                  >
                    <Icon className="w-4 h-4 shrink-0" aria-hidden="true" />
                    <span>{item.label}</span>
                  </button>
                );
              })}
            </nav>
          </aside>
        </div>
      )}

      {/* Main Column */}
      <div className="flex-1 min-w-0 flex flex-col">
        {/* Strict Top Bar Contract */}
        <header className="h-16 px-4 sm:px-6 lg:px-8 bg-white border-b border-slate-200 flex items-center justify-between gap-6 shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <button
              type="button"
              onClick={() => setMobileNavOpen(true)}
              aria-label="Open navigation menu"
              className="lg:hidden p-2 -ml-2 text-slate-600 hover:text-slate-900 cursor-pointer"
            >
              <Menu className="w-5 h-5" />
            </button>
            <h1 className="text-sm sm:text-base font-semibold text-slate-900 truncate">
              {TAB_TITLES[activeTab]}
            </h1>
          </div>

          <button
            type="button"
            onClick={handleRunAcceptance}
            disabled={runningAcceptance}
            className="px-4 py-2 min-h-[40px] text-xs sm:text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer"
          >
            {runningAcceptance ? 'Verifying...' : 'Run Acceptance Suite'}
          </button>
        </header>

        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          {loadError && (
            <div role="alert" className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md text-sm text-red-800">
              {loadError}
            </div>
          )}

          {loading || !state ? (
            <div className="space-y-4" aria-busy="true">
              <div className="h-32 bg-white border border-slate-200 rounded-lg animate-pulse" />
              <div className="h-64 bg-white border border-slate-200 rounded-lg animate-pulse" />
            </div>
          ) : (
            <>
              {activeTab === 'orchestrator' && (
                <OrchestratorView
                  state={state}
                  lastRun={lastRun}
                  onRunComplete={setLastRun}
                  onRefreshState={loadState}
                />
              )}

              {activeTab === 'safety' && (
                <SafetyOpsView state={state} onRefreshState={loadState} />
              )}

              {activeTab === 'memory' && (
                <MemoryDreamSkillsView state={state} onRefreshState={loadState} />
              )}

              {activeTab === 'adapters' && (
                <AdaptersVerifyView
                  files={files}
                  acceptanceReport={acceptanceReport}
                  runningAcceptance={runningAcceptance}
                  onRunAcceptance={handleRunAcceptance}
                  onRebuildAdapters={handleRebuildAdapters}
                />
              )}

              {activeTab === 'source' && <SourceTreeView files={files} />}
            </>
          )}
        </main>
      </div>
    </div>
  );
}
