import React, { useMemo, useState } from 'react';
import { Copy, Check, Download, Search } from 'lucide-react';
import { filterPluginFiles } from '../lib/aetherloomLogic';
import type { PluginFileEntry } from '../types';

interface SourceTreeViewProps {
  files: PluginFileEntry[];
}

const CATEGORIES: Array<{ id: string; label: string }> = [
  { id: 'all', label: 'All Files' },
  { id: 'canonical', label: 'Canonical' },
  { id: 'skills', label: 'Skills' },
  { id: 'agents', label: '18 Agents' },
  { id: 'core', label: 'Core Runtime' },
  { id: 'benchmarks', label: 'Benchmarks' },
  { id: 'adapters', label: 'Adapters' },
  { id: 'tests', label: 'Tests' },
  { id: 'docs', label: 'README' },
];

export function SourceTreeView({ files }: SourceTreeViewProps) {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('all');
  const [selectedPath, setSelectedPath] = useState<string>('manifest.json');
  const [copied, setCopied] = useState(false);

  const filtered = useMemo(
    () => filterPluginFiles(files, query, category),
    [files, query, category],
  );

  const selectedFile =
    filtered.find((f) => f.path === selectedPath) ||
    files.find((f) => f.path === selectedPath) ||
    filtered[0] ||
    null;

  function handleCopy() {
    if (!selectedFile) return;
    navigator.clipboard?.writeText(selectedFile.content).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="space-y-6">
      <section aria-label="Complete plugin source tree" className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              Complete AetherLoom Plugin Source Tree ({files.length} files)
            </h2>
            <p className="text-sm text-slate-600 mt-0.5">
              Every canonical file, 5 core skills, 18 subagents, Python SQLite FTS5 core, 6 benchmark tasks, generated host adapters, and acceptance suite in full.
            </p>
          </div>
          <a
            href="/api/download-zip"
            download="aetherloom-supergravity-plugin.zip"
            className="inline-flex items-center gap-2 px-4 py-2 min-h-[40px] text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md whitespace-nowrap shrink-0"
          >
            <Download className="w-4 h-4" aria-hidden="true" />
            Download Plugin (.zip)
          </a>
        </div>

        {/* Search and Category Filter Controls */}
        <div className="px-6 py-3.5 bg-slate-50 border-b border-slate-200 flex flex-col lg:flex-row lg:items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-1" role="group" aria-label="Filter files by category">
            {CATEGORIES.map((cat) => (
              <button
                key={cat.id}
                type="button"
                onClick={() => setCategory(cat.id)}
                className={`px-2.5 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                  category === cat.id
                    ? 'bg-white text-slate-900 border border-slate-200'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>

          <div className="relative w-full lg:w-72">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" aria-hidden="true" />
            <label htmlFor="tree-filter" className="sr-only">Filter plugin files</label>
            <input
              id="tree-filter"
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Filter path or role..."
              className="w-full pl-9 pr-3 py-1.5 text-sm text-slate-900 bg-white border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
          </div>
        </div>

        {/* Split Explorer */}
        <div className="grid grid-cols-1 lg:grid-cols-12 min-h-[540px]">
          <div className="lg:col-span-4 border-b lg:border-b-0 lg:border-r border-slate-200 divide-y divide-slate-100 max-h-[640px] overflow-y-auto">
            {filtered.length === 0 ? (
              <div className="p-6 text-sm text-slate-500">No files match &ldquo;{query}&rdquo;.</div>
            ) : (
              filtered.map((file) => {
                const active = selectedFile?.path === file.path;
                return (
                  <button
                    key={file.path}
                    type="button"
                    onClick={() => setSelectedPath(file.path)}
                    className={`w-full text-left px-4 py-3 transition-colors cursor-pointer ${
                      active ? 'bg-blue-50' : 'hover:bg-slate-50'
                    }`}
                  >
                    <div className={`text-xs font-mono truncate ${active ? 'font-semibold text-blue-800' : 'font-medium text-slate-900'}`}>
                      aetherloom/{file.path}
                    </div>
                    <div className="text-xs text-slate-600 mt-0.5 line-clamp-2">{file.role}</div>
                    <div className="text-[11px] font-mono text-slate-400 mt-1 tabular-nums">
                      {file.category} · {file.lines} lines · {file.sizeBytes.toLocaleString()} B
                    </div>
                  </button>
                );
              })
            )}
          </div>

          <div className="lg:col-span-8 flex flex-col">
            {selectedFile ? (
              <>
                <div className="px-5 py-3.5 border-b border-slate-200 flex flex-wrap items-start justify-between gap-3 bg-white">
                  <div>
                    <div className="text-sm font-mono font-semibold text-slate-900">
                      aetherloom/{selectedFile.path}
                    </div>
                    <p className="text-xs text-slate-600 mt-0.5">{selectedFile.role}</p>
                  </div>
                  <button
                    type="button"
                    onClick={handleCopy}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-md whitespace-nowrap shrink-0 cursor-pointer"
                  >
                    {copied ? <Check className="w-3.5 h-3.5 text-emerald-700" /> : <Copy className="w-3.5 h-3.5" />}
                    {copied ? 'Copied File' : 'Copy Content'}
                  </button>
                </div>
                <pre className="flex-1 p-5 bg-slate-900 text-slate-100 text-xs font-mono overflow-auto max-h-[560px] leading-relaxed">
                  {selectedFile.content}
                </pre>
              </>
            ) : (
              <div className="p-8 text-sm text-slate-500">Select a file from the plugin tree to inspect its full content.</div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
