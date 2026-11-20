import React, { useState } from 'react';
import { Play } from 'lucide-react';
import {
  AGENT_ROSTER,
  evaluateMeterHealth,
  formatPct,
  formatUsd,
} from '../lib/aetherloomLogic';
import type { OrchestrationResult, WorkbenchState } from '../types';

interface OrchestratorViewProps {
  state: WorkbenchState;
  lastRun: OrchestrationResult | null;
  onRunComplete: (result: OrchestrationResult) => void;
  onRefreshState: () => Promise<void>;
}

const PRESET_GOALS = [
  {
    label: 'Multi-file refactor (swarm)',
    goal: 'Multi-file refactor to rename auth session helpers across modules',
    media: '',
  },
  {
    label: 'Multi-day research (teamwork)',
    goal: 'Multi-day deep dive research and architecture audit on SQLite FTS5 BM25 retrieval',
    media: '',
  },
  {
    label: 'Mixed sprint + audit (hybrid)',
    goal: 'Multi-day research and parallel multi-file refactor with milestone verification',
    media: '',
  },
  {
    label: 'Creative + Veo check',
    goal: 'Multi-file landing page refactor with Veo promo clip generation',
    media: 'generate_video',
  },
];

const LAYERS: Array<{ id: 'L0' | 'L1' | 'L2' | 'L3' | 'L4'; title: string }> = [
  { id: 'L0', title: 'L0 Command' },
  { id: 'L1', title: 'L1 Build' },
  { id: 'L2', title: 'L2 Research' },
  { id: 'L3', title: 'L3 Quality' },
  { id: 'L4', title: 'L4 Creative and Ops' },
];

export function OrchestratorView({
  state,
  lastRun,
  onRunComplete,
  onRefreshState,
}: OrchestratorViewProps) {
  const [goal, setGoal] = useState(PRESET_GOALS[0].goal);
  const [mediaTool, setMediaTool] = useState<string>('');
  const [tierOverride, setTierOverride] = useState<'free' | 'paid'>('free');
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const meter = lastRun?.meter_summary ?? state.meter_summary;
  const health = evaluateMeterHealth(meter);
  const activeAgentSet = new Set(lastRun?.route.active_agents ?? []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!goal.trim()) {
      setError('Enter a goal for /supergravity before running.');
      return;
    }
    setError(null);
    setRunning(true);
    try {
      const resp = await fetch('/api/orchestrate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          goal: goal.trim(),
          tier: tierOverride,
          requested_media_tool: mediaTool || null,
        }),
      });
      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.error || 'Orchestration request failed.');
      }
      onRunComplete(data as OrchestrationResult);
      await onRefreshState();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-8">
      {/* Meter Telemetry Strip (3 Separate Required Metrics + Strategy) */}
      <section aria-label="Meter telemetry summary" className="bg-white border border-slate-200 rounded-lg">
        <div className="px-6 py-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Meter Telemetry and Accuracy Floor</h2>
            <p className="text-sm text-slate-600 mt-0.5">
              Measured across {meter.record_count} recorded subagent tasks · Never compresses relevant context
            </p>
          </div>
          <div className="text-sm text-slate-600 tabular-nums">
            Strategy:{' '}
            <span className={meter.accuracy_regression ? 'font-semibold text-amber-700' : 'font-semibold text-slate-900'}>
              {meter.recommended_strategy}
            </span>
            <span className="mx-2 text-slate-300" aria-hidden="true">/</span>
            Total Spend: <span className="font-mono font-medium text-slate-900">{formatUsd(meter.cost_usd)}</span>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-slate-200">
          <div className="p-6">
            <div className="text-xs font-medium text-slate-500">Memory-Turn Input Savings</div>
            <div className="mt-2 text-2xl font-semibold font-mono tabular-nums text-slate-900">
              {formatPct(meter.memory_turn_input_savings_pct)}
            </div>
            <div className="mt-1 text-xs text-slate-600">
              Target ~85% · {health.memorySavingsOnTarget ? 'On target' : 'Below target'}
            </div>
          </div>

          <div className="p-6">
            <div className="text-xs font-medium text-slate-500">Overall Per-Task Savings</div>
            <div className="mt-2 text-2xl font-semibold font-mono tabular-nums text-slate-900">
              {formatPct(meter.overall_task_savings_pct)}
            </div>
            <div className="mt-1 text-xs text-slate-600">
              Target 40–60% · {health.overallSavingsOnTarget ? 'On target' : 'Check routing'}
            </div>
          </div>

          <div className="p-6">
            <div className="text-xs font-medium text-slate-500">Measured Pass Rate</div>
            <div className="mt-2 text-2xl font-semibold font-mono tabular-nums text-slate-900">
              {formatPct(meter.pass_rate)}
            </div>
            <div className={`mt-1 text-xs font-medium ${health.passRateHealthy ? 'text-emerald-700' : 'text-red-700'}`}>
              Floor 90–95% · Delta {meter.pass_rate_change_pct >= 0 ? '+' : ''}
              {meter.pass_rate_change_pct.toFixed(1)}%
            </div>
          </div>

          <div className="p-6">
            <div className="text-xs font-medium text-slate-500">Recorded Token Ledger</div>
            <div className="mt-2 text-lg font-semibold font-mono tabular-nums text-slate-900">
              {meter.input_tokens.toLocaleString()} in / {meter.output_tokens.toLocaleString()} out
            </div>
            <div className="mt-1 text-xs text-slate-600 font-mono tabular-nums">
              {meter.cached_tokens.toLocaleString()} cached prefix tokens
            </div>
          </div>
        </div>
      </section>

      {/* /supergravity Command Runner */}
      <section aria-label="Supergravity command runner" className="bg-white border border-slate-200 rounded-lg p-6">
        <div className="flex flex-wrap items-baseline justify-between gap-2 mb-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Run /supergravity Command</h2>
            <p className="text-sm text-slate-600 mt-0.5">
              Commander records the goal, Router classifies the execution mode, Archivist queries SQLite FTS5, and traces append to runs/&lt;id&gt;/board.ndjson.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 mb-4" role="group" aria-label="Preset routing goals">
          {PRESET_GOALS.map((preset) => (
            <button
              key={preset.label}
              type="button"
              onClick={() => {
                setGoal(preset.goal);
                setMediaTool(preset.media);
                setError(null);
              }}
              className="px-3 py-1.5 min-h-[36px] text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer"
            >
              {preset.label}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="supergravity-goal" className="block text-sm font-medium text-slate-700 mb-1.5">
              Command Goal
            </label>
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center font-mono text-sm text-slate-400">
                  /supergravity
                </span>
                <input
                  id="supergravity-goal"
                  type="text"
                  value={goal}
                  onChange={(e) => setGoal(e.target.value)}
                  placeholder="Describe the engineering goal..."
                  className="w-full pl-32 pr-4 py-2.5 text-sm text-slate-900 bg-white border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600"
                />
              </div>
              <button
                type="submit"
                disabled={running}
                className="inline-flex items-center justify-center gap-2 px-5 py-2.5 min-h-[42px] text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer"
              >
                <Play className="w-4 h-4" aria-hidden="true" />
                {running ? 'Running...' : 'Run Command'}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
            <div>
              <label htmlFor="orch-tier" className="block text-xs font-medium text-slate-600 mb-1">
                Active API Key Tier
              </label>
              <select
                id="orch-tier"
                value={tierOverride}
                onChange={(e) => setTierOverride(e.target.value as 'free' | 'paid')}
                className="w-full px-3 py-2 text-sm text-slate-900 bg-white border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-600"
              >
                <option value="free">Free-Tier Key (Gemini 3.6 Flash · ~15 RPM / 1,500 RPD · Veo disabled)</option>
                <option value="paid">Funded Paid Key (&gt;=$5 deposited · Veo gated by Warden)</option>
              </select>
            </div>

            <div>
              <label htmlFor="orch-media" className="block text-xs font-medium text-slate-600 mb-1">
                Optional Media MCP Tool Call (Warden Preflight)
              </label>
              <select
                id="orch-media"
                value={mediaTool}
                onChange={(e) => setMediaTool(e.target.value)}
                className="w-full px-3 py-2 text-sm text-slate-900 bg-white border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-600"
              >
                <option value="">None (code and research subagents only)</option>
                <option value="generate_image">Vision · generate_image (Nano Banana)</option>
                <option value="generate_speech">Griot · generate_speech (Gemini TTS)</option>
                <option value="generate_video">Vision · generate_video (Veo — Paid Key Only)</option>
              </select>
            </div>
          </div>

          {error && (
            <p role="alert" className="text-sm text-red-700 font-medium">
              {error}
            </p>
          )}
        </form>

        {/* Live Commander Summary & Append-Only Board Trace */}
        {lastRun && (
          <div className="mt-6 pt-6 border-t border-slate-200 space-y-4" data-testid="orchestration-output">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <div className="text-xs text-slate-500">
                  Run <span className="font-mono text-slate-800">{lastRun.run_id}</span>
                  <span className="mx-2" aria-hidden="true">·</span>
                  Mode: <span className="font-mono font-semibold text-blue-700">{lastRun.mode}</span>
                  <span className="mx-2" aria-hidden="true">·</span>
                  Status:{' '}
                  <span className={lastRun.status === 'completed' ? 'font-semibold text-emerald-700' : 'font-semibold text-amber-700'}>
                    {lastRun.status}
                  </span>
                </div>
                <p className="text-sm text-slate-700 mt-1">{lastRun.route.rationale}</p>
              </div>
              <div className="text-xs font-mono text-slate-500">
                Trace: {lastRun.board_path}
              </div>
            </div>

            {lastRun.blockers.length > 0 && (
              <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-md text-sm text-amber-900">
                <div className="font-semibold">Blocker Reported by Commander</div>
                <ul className="mt-1 list-disc pl-5 space-y-0.5">
                  {lastRun.blockers.map((b, idx) => (
                    <li key={idx}>{b}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div>
                <h3 className="text-xs font-semibold text-slate-700 mb-2">
                  Append-Only Board Trace ({lastRun.board_events.length} events)
                </h3>
                <pre className="p-3.5 bg-slate-900 text-slate-100 rounded-md text-xs font-mono overflow-x-auto max-h-64 leading-relaxed">
                  {lastRun.board_events.map((ev) => JSON.stringify(ev)).join('\n')}
                </pre>
              </div>

              <div>
                <h3 className="text-xs font-semibold text-slate-700 mb-2">
                  Archivist FTS5 Memory Hits ({lastRun.memory.hits.length} hits · {lastRun.memory.tokens_used}/{lastRun.memory.budget_tokens} tokens)
                </h3>
                {lastRun.memory.hits.length === 0 ? (
                  <p className="text-sm text-slate-500 py-3">
                    No matching fragments for this query; subagents ran with clean prompt prefixes.
                  </p>
                ) : (
                  <div className="divide-y divide-slate-200 border border-slate-200 rounded-md max-h-64 overflow-y-auto">
                    {lastRun.memory.hits.map((hit) => (
                      <div key={`${hit.source}-${hit.id}`} className="p-3 text-xs">
                        <div className="flex items-center justify-between gap-2 text-slate-500 font-mono">
                          <span className="font-semibold text-slate-800">{hit.title}</span>
                          <span className="tabular-nums">BM25 {hit.bm25.toFixed(3)} · {hit.tokens} tok</span>
                        </div>
                        <p className="mt-1 text-slate-700 leading-relaxed">{hit.content}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </section>

      {/* 5-Layer, 18-Subagent Architecture Table */}
      <section aria-label="18 subagents across 5 layers" className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Five-Layer Agent Architecture (18 Subagents)</h2>
            <p className="text-sm text-slate-600 mt-0.5">
              Idle subagents hold zero tokens. Only Vision and Griot call billed media MCP endpoints, strictly gated by Warden.
            </p>
          </div>
          {lastRun && (
            <div className="text-xs text-slate-600 font-mono tabular-nums">
              {activeAgentSet.size} / 18 active in {lastRun.mode} run
            </div>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-xs font-medium text-slate-500">
                <th className="py-2.5 px-6">Layer</th>
                <th className="py-2.5 px-4">Agent</th>
                <th className="py-2.5 px-4">Core Responsibility</th>
                <th className="py-2.5 px-4">Guardrail / Billing</th>
                <th className="py-2.5 px-6 text-right">Assigned Model</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-sm">
              {LAYERS.flatMap((layer) =>
                AGENT_ROSTER.filter((a) => a.layer === layer.id).map((agent) => {
                  const isActive = activeAgentSet.has(agent.id);
                  const assignedModel = lastRun?.route.model_assignments[agent.id];
                  return (
                    <tr
                      key={agent.id}
                      className={isActive ? 'bg-blue-50/40' : 'hover:bg-slate-50 transition-colors'}
                    >
                      <td className="py-2.5 px-6 font-mono text-xs text-slate-500 whitespace-nowrap">
                        {layer.title}
                      </td>
                      <td className="py-2.5 px-4 font-semibold text-slate-900 whitespace-nowrap">
                        {agent.name}
                      </td>
                      <td className="py-2.5 px-4 text-slate-700">{agent.responsibility}</td>
                      <td className="py-2.5 px-4 text-xs whitespace-nowrap">
                        {agent.billed ? (
                          <span className="font-medium text-amber-700">Warden required (billed MCP)</span>
                        ) : agent.id === 'natalie' ? (
                          <span className="font-medium text-slate-700">Ops only (non-coder)</span>
                        ) : (
                          <span className="text-slate-500">Free-tier standard</span>
                        )}
                      </td>
                      <td className="py-2.5 px-6 text-right font-mono text-xs text-slate-600 whitespace-nowrap">
                        {assignedModel ? assignedModel : lastRun ? 'Idle (0 tokens)' : 'On demand'}
                      </td>
                    </tr>
                  );
                }),
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
