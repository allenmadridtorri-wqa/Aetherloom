import React, { useState } from 'react';
import { Search, Plus, GitCompare, Award } from 'lucide-react';
import type { MemorySearchResult, WorkbenchState } from '../types';

interface MemoryDreamSkillsViewProps {
  state: WorkbenchState;
  onRefreshState: () => Promise<void>;
}

export function MemoryDreamSkillsView({
  state,
  onRefreshState,
}: MemoryDreamSkillsViewProps) {
  const [searchQuery, setSearchQuery] = useState('FTS5 BM25 Warden');
  const [budgetTokens, setBudgetTokens] = useState('800');
  const [searchResult, setSearchResult] = useState<MemorySearchResult | null>(null);
  const [searching, setSearching] = useState(false);

  const [noteProject, setNoteProject] = useState('aetherloom');
  const [noteBody, setNoteBody] = useState('');
  const [savingNote, setSavingNote] = useState(false);

  const [dreamRunning, setDreamRunning] = useState(false);
  const [dreamMessage, setDreamMessage] = useState<string | null>(null);

  const [skillName, setSkillName] = useState('worktree-evidence-gate');
  const [skillInstructions, setSkillInstructions] = useState(
    'Isolate edits in a git worktree, inspect diff, run test for verbatim output evidence, retrieve FTS5 BM25 slice within budget, enforce Warden cap approval, emit free-tier Veo warning, and output Dream preview patch pending.',
  );
  const [evaluatingSkill, setEvaluatingSkill] = useState(false);
  const [skillEvalMsg, setSkillEvalMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSearching(true);
    try {
      const resp = await fetch('/api/memory/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: searchQuery,
          k: 5,
          context_budget_tokens: Number(budgetTokens) || 800,
        }),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || 'FTS5 search failed.');
      setSearchResult(data as MemorySearchResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSearching(false);
    }
  }

  async function handleAddNote(e: React.FormEvent) {
    e.preventDefault();
    if (!noteBody.trim()) {
      setError('Enter note text before writing to SQLite FTS5.');
      return;
    }
    setError(null);
    setSavingNote(true);
    try {
      const resp = await fetch('/api/memory/note', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project: noteProject, body: noteBody.trim() }),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || 'Failed to save note.');
      setNoteBody('');
      await onRefreshState();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSavingNote(false);
    }
  }

  async function handleDreamPreview() {
    setError(null);
    setDreamRunning(true);
    setDreamMessage(null);
    try {
      const resp = await fetch('/api/dream/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force: true }),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || 'Dream preview failed.');
      setDreamMessage(
        data.executed
          ? `Preview patch created (${data.diff.id}) with status pending. Zero live memory records were modified.`
          : data.reason,
      );
      await onRefreshState();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setDreamRunning(false);
    }
  }

  async function handleApproveDream(diffId: string, approver: 'user' | 'SuccessAuditor') {
    setError(null);
    try {
      const resp = await fetch('/api/dream/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ diff_id: diffId, approved_by: approver }),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || 'Approval failed.');
      await onRefreshState();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleSkillEvaluate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSkillEvalMsg(null);
    setEvaluatingSkill(true);
    try {
      const resp = await fetch('/api/skills/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: skillName,
          description: 'Trajectory-derived procedural skill candidate',
          instructions: skillInstructions,
        }),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || 'Skill benchmark failed.');
      const res = data.result;
      setSkillEvalMsg(
        res.promoted
          ? `Promoted to ${res.destination} (${res.evaluation.candidate_pass_rate}% pass rate vs ${res.evaluation.baseline_pass_rate}% baseline, ${res.evaluation.token_reduction_pct}% token reduction).`
          : res.failure_reason,
      );
      await onRefreshState();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setEvaluatingSkill(false);
    }
  }

  return (
    <div className="space-y-8">
      {error && (
        <div role="alert" className="p-3.5 bg-red-50 border border-red-200 rounded-md text-sm text-red-800">
          {error}
        </div>
      )}

      {/* SQLite FTS5 BM25 Search + Note Writer */}
      <section aria-label="SQLite FTS5 BM25 memory layer" className="bg-white border border-slate-200 rounded-lg p-6">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <div>
            <h2 className="text-base font-semibold text-slate-900">SQLite FTS5 Memory (Archivist BM25 Search)</h2>
            <p className="text-sm text-slate-600 mt-0.5">
              Indexes notes.body, code_map.summary, and sessions.summary with BM25 ranking. Drops lower-ranked hits instead of compressing relevant text.
            </p>
          </div>
          <div className="text-xs font-mono text-slate-500 tabular-nums">
            {state.notes.length} notes · {state.code_map.length} code_map · {state.sessions.length} sessions
          </div>
        </div>

        <form onSubmit={handleSearch} className="mt-4 flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <label htmlFor="fts-query" className="sr-only">Search FTS5 memory</label>
            <input
              id="fts-query"
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search notes, code_map, and sessions via BM25..."
              className="w-full px-3.5 py-2 text-sm text-slate-900 bg-white border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
          </div>
          <div className="w-36">
            <label htmlFor="fts-budget" className="sr-only">Context token budget</label>
            <input
              id="fts-budget"
              type="number"
              min="50"
              max="4000"
              value={budgetTokens}
              onChange={(e) => setBudgetTokens(e.target.value)}
              title="Caller context token budget"
              className="w-full px-3 py-2 text-sm font-mono tabular-nums text-slate-900 bg-white border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
          </div>
          <button
            type="submit"
            disabled={searching}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 min-h-[40px] text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md whitespace-nowrap shrink-0 cursor-pointer"
          >
            <Search className="w-4 h-4" aria-hidden="true" />
            {searching ? 'Searching...' : 'Search BM25'}
          </button>
        </form>

        {searchResult && (
          <div className="mt-4 border border-slate-200 rounded-md overflow-hidden" data-testid="fts-results">
            <div className="px-4 py-2 bg-slate-50 border-b border-slate-200 flex items-center justify-between text-xs font-mono text-slate-600 tabular-nums">
              <span>Top-{searchResult.k} BM25 Results ({searchResult.hits.length} matched)</span>
              <span>Budget used: {searchResult.tokens_used} / {searchResult.budget_tokens} tokens</span>
            </div>
            {searchResult.hits.length === 0 ? (
              <p className="p-4 text-sm text-slate-500">No FTS5 matches for &ldquo;{searchResult.query}&rdquo;.</p>
            ) : (
              <div className="divide-y divide-slate-200">
                {searchResult.hits.map((hit) => (
                  <div key={`${hit.source}-${hit.id}`} className="p-3.5 text-sm">
                    <div className="flex items-center justify-between gap-2 text-xs font-mono text-slate-500">
                      <span className="font-semibold text-slate-900">{hit.source} / {hit.title}</span>
                      <span className="tabular-nums">BM25 {hit.bm25.toFixed(4)} · {hit.tokens} tok</span>
                    </div>
                    <p className="mt-1 text-slate-700">{hit.content}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        <form onSubmit={handleAddNote} className="mt-6 pt-5 border-t border-slate-200 grid grid-cols-1 sm:grid-cols-12 gap-3">
          <div className="sm:col-span-3">
            <label htmlFor="note-project" className="block text-xs font-medium text-slate-600 mb-1">Project</label>
            <input
              id="note-project"
              type="text"
              value={noteProject}
              onChange={(e) => setNoteProject(e.target.value)}
              className="w-full px-3 py-2 text-sm text-slate-900 bg-white border border-slate-300 rounded-md"
            />
          </div>
          <div className="sm:col-span-7">
            <label htmlFor="note-body" className="block text-xs font-medium text-slate-600 mb-1">Write New Memory Note</label>
            <input
              id="note-body"
              type="text"
              value={noteBody}
              onChange={(e) => setNoteBody(e.target.value)}
              placeholder="e.g. Router reverts to conservative strategy whenever pass_rate drops below 90%."
              className="w-full px-3 py-2 text-sm text-slate-900 bg-white border border-slate-300 rounded-md"
            />
          </div>
          <div className="sm:col-span-2 flex items-end">
            <button
              type="submit"
              disabled={savingNote}
              className="w-full inline-flex items-center justify-center gap-1.5 px-3 py-2 min-h-[40px] text-sm font-medium text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-md whitespace-nowrap cursor-pointer"
            >
              <Plus className="w-4 h-4" aria-hidden="true" />
              Save Note
            </button>
          </div>
        </form>
      </section>

      {/* Dream Propose-then-Commit Preview */}
      <section aria-label="Dream propose-then-commit preview" className="bg-white border border-slate-200 rounded-lg p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Dream Consolidation (Propose-Then-Commit Preview)</h2>
            <p className="text-sm text-slate-600 mt-0.5">
              Scheduled by N.A.T.A.L.I.E. after &gt;=24h and &gt;=5 sessions. Default mode is preview—writes unified diffs to dream_diffs/&lt;id&gt;.patch without mutating live memory.
            </p>
          </div>
          <button
            type="button"
            onClick={handleDreamPreview}
            disabled={dreamRunning}
            className="inline-flex items-center gap-2 px-4 py-2 min-h-[40px] text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-md whitespace-nowrap shrink-0 cursor-pointer"
          >
            <GitCompare className="w-4 h-4" aria-hidden="true" />
            {dreamRunning ? 'Running Preview...' : 'Run Dream Preview'}
          </button>
        </div>

        <div className="mt-3 text-xs font-mono text-slate-600 tabular-nums">
          Schedule Gate: {state.dream_gate.sessions_since_last} / {state.dream_gate.min_sessions_required} sessions
          <span className="mx-2 text-slate-300" aria-hidden="true">·</span>
          {state.dream_gate.hours_elapsed}h / {state.dream_gate.min_hours_required}h elapsed
          <span className="mx-2 text-slate-300" aria-hidden="true">·</span>
          Phases: Collect -&gt; Propose -&gt; Validate -&gt; Commit-as-pending
        </div>

        {dreamMessage && (
          <div className="mt-4 p-3 bg-slate-50 border border-slate-200 rounded-md text-sm text-slate-800">
            {dreamMessage}
          </div>
        )}

        <div className="mt-5 space-y-4">
          {state.dream_diffs.length === 0 ? (
            <p className="text-sm text-slate-500">
              No Dream diffs generated yet. Click &ldquo;Run Dream Preview&rdquo; to create a pending unified diff patch.
            </p>
          ) : (
            state.dream_diffs.slice(0, 3).map((diff) => (
              <div key={diff.id} className="border border-slate-200 rounded-md overflow-hidden">
                <div className="px-4 py-2.5 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2 text-xs">
                  <div className="font-mono text-slate-800">
                    <span className="font-semibold">{diff.id}</span>
                    <span className="mx-2 text-slate-400" aria-hidden="true">·</span>
                    <span>Status: </span>
                    <span className={diff.status === 'approved' ? 'font-semibold text-emerald-700' : 'font-semibold text-amber-700'}>
                      {diff.status}
                    </span>
                    {diff.approved_by && <span className="ml-2 text-slate-500">(by {diff.approved_by})</span>}
                  </div>
                  {diff.status === 'pending' && (
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => handleApproveDream(diff.id, 'user')}
                        aria-label={`Approve ${diff.id} as user`}
                        className="px-2.5 py-1 text-xs font-medium text-white bg-emerald-700 hover:bg-emerald-800 rounded cursor-pointer"
                      >
                        Approve as User
                      </button>
                      <button
                        type="button"
                        onClick={() => handleApproveDream(diff.id, 'SuccessAuditor')}
                        aria-label={`Approve ${diff.id} as SuccessAuditor`}
                        className="px-2.5 py-1 text-xs font-medium text-slate-700 bg-slate-200 hover:bg-slate-300 rounded cursor-pointer"
                      >
                        Approve as SuccessAuditor
                      </button>
                    </div>
                  )}
                </div>
                <pre className="p-3.5 bg-slate-900 text-slate-100 text-xs font-mono overflow-x-auto max-h-52">
                  {diff.patch_content || '# Patch file empty'}
                </pre>
              </div>
            ))
          )}
        </div>
      </section>

      {/* Benchmark-Gated Skill Learning */}
      <section aria-label="Skill learning benchmark gate" className="bg-white border border-slate-200 rounded-lg p-6">
        <h2 className="text-base font-semibold text-slate-900">Benchmark-Gated Skill Learning</h2>
        <p className="text-sm text-slate-600 mt-0.5">
          Candidates are written to skills/candidates/, tested against 6 benchmark tasks vs baseline, and promoted solely to skills/learned/. Core skills in skills/ are immutable.
        </p>

        <form onSubmit={handleSkillEvaluate} className="mt-4 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label htmlFor="skill-name" className="block text-xs font-medium text-slate-600 mb-1">
                Candidate Skill Slug
              </label>
              <input
                id="skill-name"
                type="text"
                value={skillName}
                onChange={(e) => setSkillName(e.target.value)}
                className="w-full px-3 py-2 text-sm font-mono text-slate-900 bg-white border border-slate-300 rounded-md"
              />
            </div>
            <div className="sm:col-span-2">
              <label htmlFor="skill-instructions" className="block text-xs font-medium text-slate-600 mb-1">
                Candidate Trajectory Procedure
              </label>
              <input
                id="skill-instructions"
                type="text"
                value={skillInstructions}
                onChange={(e) => setSkillInstructions(e.target.value)}
                className="w-full px-3 py-2 text-sm text-slate-900 bg-white border border-slate-300 rounded-md"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={evaluatingSkill}
            className="inline-flex items-center gap-2 px-4 py-2 min-h-[40px] text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-md whitespace-nowrap cursor-pointer"
          >
            <Award className="w-4 h-4" aria-hidden="true" />
            {evaluatingSkill ? 'Running Benchmarks...' : 'Draft and Benchmark Candidate'}
          </button>
        </form>

        {skillEvalMsg && (
          <div className="mt-4 p-3 bg-slate-50 border border-slate-200 rounded-md text-sm text-slate-800">
            {skillEvalMsg}
          </div>
        )}

        <div className="mt-5 overflow-x-auto">
          <table className="w-full text-left border-collapse text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs font-medium text-slate-500">
                <th className="py-2 pr-4">Skill</th>
                <th className="py-2 px-4">Path</th>
                <th className="py-2 px-4">Status</th>
                <th className="py-2 pl-4 text-right">Benchmark Score</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {state.skills.map((s) => (
                <tr key={s.name}>
                  <td className="py-2.5 pr-4 font-mono font-medium text-slate-900">{s.name}</td>
                  <td className="py-2.5 px-4 font-mono text-xs text-slate-600">{s.path}</td>
                  <td className="py-2.5 px-4 text-xs font-medium">
                    <span
                      className={
                        s.status === 'promoted' || s.status === 'core'
                          ? 'text-emerald-700'
                          : s.status === 'rejected'
                            ? 'text-red-700'
                            : 'text-amber-700'
                      }
                    >
                      {s.status}
                    </span>
                  </td>
                  <td className="py-2.5 pl-4 text-right font-mono text-xs tabular-nums text-slate-700">
                    {s.benchmark_score != null ? `${s.benchmark_score.toFixed(1)}%` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
