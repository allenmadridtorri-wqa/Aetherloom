import React, { useState } from 'react';
import { CheckCircle2, XCircle, RefreshCw, Copy, Check } from 'lucide-react';
import { HOST_ADAPTER_SPECS } from '../lib/aetherloomLogic';
import type { AcceptanceReport, PluginFileEntry } from '../types';

interface AdaptersVerifyViewProps {
  files: PluginFileEntry[];
  acceptanceReport: AcceptanceReport | null;
  runningAcceptance: boolean;
  onRunAcceptance: () => Promise<void>;
  onRebuildAdapters: () => Promise<void>;
}

export function AdaptersVerifyView({
  files,
  acceptanceReport,
  runningAcceptance,
  onRunAcceptance,
  onRebuildAdapters,
}: AdaptersVerifyViewProps) {
  const [selectedHost, setSelectedHost] = useState(HOST_ADAPTER_SPECS[0].id);
  const [selectedFilePath, setSelectedFilePath] = useState<string>('');
  const [rebuilding, setRebuilding] = useState(false);
  const [copiedPath, setCopiedPath] = useState<string | null>(null);

  const currentSpec =
    HOST_ADAPTER_SPECS.find((h) => h.id === selectedHost) || HOST_ADAPTER_SPECS[0];
  const hostFiles = files.filter((f) => f.path.startsWith(currentSpec.pathPrefix));
  const activeFile =
    hostFiles.find((f) => f.path === selectedFilePath) || hostFiles[0] || null;

  async function handleRebuild() {
    setRebuilding(true);
    try {
      await onRebuildAdapters();
    } finally {
      setRebuilding(false);
    }
  }

  function handleCopy(text: string, key: string) {
    navigator.clipboard?.writeText(text).catch(() => {});
    setCopiedPath(key);
    setTimeout(() => setCopiedPath(null), 1500);
  }

  return (
    <div className="space-y-8">
      {/* Live 10-Check Acceptance Test Suite */}
      <section aria-label="Acceptance verification suite" className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Acceptance Test Suite (10 Non-Negotiable Checks)</h2>
            <p className="text-sm text-slate-600 mt-0.5">
              Executes python3 aetherloom/tests/test_acceptance.py directly against SQLite FTS5, Router, Dream, Meter, Warden, Free-Tier Probe, and generated adapters.
            </p>
          </div>
          <div className="flex items-center gap-3">
            {acceptanceReport && (
              <span
                className={`text-sm font-mono font-semibold tabular-nums ${
                  acceptanceReport.all_passed ? 'text-emerald-700' : 'text-red-700'
                }`}
              >
                {acceptanceReport.passed}/{acceptanceReport.total} Passed
              </span>
            )}
            <button
              type="button"
              onClick={onRunAcceptance}
              disabled={runningAcceptance}
              className="px-4 py-2 min-h-[40px] text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-md whitespace-nowrap shrink-0 cursor-pointer"
            >
              {runningAcceptance ? 'Running Tests...' : 'Run Acceptance Tests'}
            </button>
          </div>
        </div>

        {!acceptanceReport ? (
          <div className="p-6 text-sm text-slate-600">
            Click &ldquo;Run Acceptance Tests&rdquo; to execute all 10 live Python verification checks.
          </div>
        ) : (
          <div className="divide-y divide-slate-200" data-testid="acceptance-results">
            {acceptanceReport.tests.map((item) => (
              <div key={item.id} className="px-6 py-3 flex items-start justify-between gap-4 text-sm">
                <div className="flex items-start gap-3">
                  {item.passed ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 mt-0.5 shrink-0" aria-hidden="true" />
                  ) : (
                    <XCircle className="w-4 h-4 text-red-600 mt-0.5 shrink-0" aria-hidden="true" />
                  )}
                  <div>
                    <div className="text-slate-900 font-medium">{item.title}</div>
                    <div className="text-xs font-mono text-slate-500 mt-0.5">{item.id}</div>
                    {item.error && (
                      <pre className="mt-2 p-2 bg-red-50 text-red-800 text-xs font-mono rounded overflow-x-auto">
                        {item.error}
                      </pre>
                    )}
                  </div>
                </div>
                <span className={`text-xs font-mono font-semibold shrink-0 ${item.passed ? 'text-emerald-700' : 'text-red-700'}`}>
                  {item.passed ? 'PASS' : 'FAIL'}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Generated Cross-Platform Host Adapters */}
      <section aria-label="Generated cross-platform host adapters" className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Generated Host Adapters (6 Targets)</h2>
            <p className="text-sm text-slate-600 mt-0.5">
              Compiled cleanly from manifest.json, AGENTS.md, skills/, and agents/ via build_adapters.py. Zero manual editing required.
            </p>
          </div>
          <button
            type="button"
            onClick={handleRebuild}
            disabled={rebuilding}
            className="inline-flex items-center gap-2 px-3.5 py-2 min-h-[38px] text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-md whitespace-nowrap shrink-0 cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${rebuilding ? 'animate-spin' : ''}`} aria-hidden="true" />
            {rebuilding ? 'Regenerating...' : 'Regenerate All Adapters'}
          </button>
        </div>

        <div className="px-6 py-3 bg-slate-50 border-b border-slate-200 flex flex-wrap gap-1.5" role="tablist" aria-label="Host adapter targets">
          {HOST_ADAPTER_SPECS.map((spec) => (
            <button
              key={spec.id}
              type="button"
              role="tab"
              aria-selected={selectedHost === spec.id}
              onClick={() => {
                setSelectedHost(spec.id);
                setSelectedFilePath('');
              }}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                selectedHost === spec.id
                  ? 'bg-white text-slate-900 border border-slate-200'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {spec.name}
            </button>
          ))}
        </div>

        <div className="p-6 space-y-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">{currentSpec.name} — {currentSpec.paradigm}</h3>
              <p className="text-sm text-slate-600 mt-1">{currentSpec.keyFacts}</p>
            </div>
            <div className="flex items-center gap-2 bg-slate-100 px-3 py-2 rounded-md">
              <code className="text-xs font-mono text-slate-800">{currentSpec.installCommand}</code>
              <button
                type="button"
                onClick={() => handleCopy(currentSpec.installCommand, `cmd-${currentSpec.id}`)}
                aria-label={`Copy install command for ${currentSpec.name}`}
                className="p-1 text-slate-500 hover:text-slate-900 cursor-pointer"
              >
                {copiedPath === `cmd-${currentSpec.id}` ? <Check className="w-3.5 h-3.5 text-emerald-700" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            <div className="lg:col-span-4 border border-slate-200 rounded-md divide-y divide-slate-200 max-h-96 overflow-y-auto">
              {hostFiles.map((file) => (
                <button
                  key={file.path}
                  type="button"
                  onClick={() => setSelectedFilePath(file.path)}
                  className={`w-full text-left px-3.5 py-2.5 text-xs font-mono transition-colors cursor-pointer ${
                    activeFile?.path === file.path
                      ? 'bg-blue-50 text-blue-800 font-semibold'
                      : 'text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  <div className="truncate">{file.path.replace(currentSpec.pathPrefix, '')}</div>
                  <div className="text-[11px] font-sans text-slate-500 mt-0.5 tabular-nums">
                    {file.lines} lines · {file.sizeBytes.toLocaleString()} B
                  </div>
                </button>
              ))}
            </div>

            <div className="lg:col-span-8 border border-slate-200 rounded-md overflow-hidden">
              {activeFile ? (
                <>
                  <div className="px-4 py-2.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between gap-2">
                    <span className="text-xs font-mono font-medium text-slate-800 truncate">
                      aetherloom/{activeFile.path}
                    </span>
                    <button
                      type="button"
                      onClick={() => handleCopy(activeFile.content, activeFile.path)}
                      aria-label={`Copy ${activeFile.path}`}
                      className="inline-flex items-center gap-1 text-xs font-medium text-slate-600 hover:text-slate-900 cursor-pointer whitespace-nowrap"
                    >
                      {copiedPath === activeFile.path ? <Check className="w-3.5 h-3.5 text-emerald-700" /> : <Copy className="w-3.5 h-3.5" />}
                      {copiedPath === activeFile.path ? 'Copied' : 'Copy'}
                    </button>
                  </div>
                  <pre className="p-4 bg-slate-900 text-slate-100 text-xs font-mono overflow-auto max-h-96 leading-relaxed">
                    {activeFile.content}
                  </pre>
                </>
              ) : (
                <div className="p-6 text-sm text-slate-500">Select a generated adapter file to inspect.</div>
              )}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
