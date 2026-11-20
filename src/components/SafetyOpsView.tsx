import React, { useState } from 'react';
import { ShieldCheck } from 'lucide-react';
import { formatUsd } from '../lib/aetherloomLogic';
import type { TierCapabilities, WardenDecision, WorkbenchState } from '../types';

interface SafetyOpsViewProps {
  state: WorkbenchState;
  onRefreshState: () => Promise<void>;
}

export function SafetyOpsView({ state, onRefreshState }: SafetyOpsViewProps) {
  const [tierMode, setTierMode] = useState<'free' | 'paid'>('free');
  const [depositedUsd, setDepositedUsd] = useState<string>('0');
  const [hardCapUsd, setHardCapUsd] = useState<string>(state.natalie.hard_cap_usd.toFixed(2));
  const [approvalThresholdUsd, setApprovalThresholdUsd] = useState<string>('0.05');
  const [agent, setAgent] = useState<'Vision' | 'Griot'>('Vision');
  const [tool, setTool] = useState<'generate_video' | 'generate_image' | 'generate_speech' | 'paid_llm_call'>('generate_video');
  const [units, setUnits] = useState<string>('1');
  const [checking, setChecking] = useState(false);
  const [updatingCap, setUpdatingCap] = useState(false);
  const [lastDecision, setLastDecision] = useState<WardenDecision | null>(null);
  const [probedTier, setProbedTier] = useState<TierCapabilities>(state.tier);
  const [error, setError] = useState<string | null>(null);

  async function handleWardenCheck(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setChecking(true);
    try {
      const resp = await fetch('/api/warden/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tier: tierMode,
          billing_deposited_usd: Number(depositedUsd) || 0,
          has_ai_pro_plan: true,
          hard_cap_usd: Number(hardCapUsd) || 0,
          approval_threshold_usd: Number(approvalThresholdUsd) || 0,
          agent,
          tool,
          units: Math.max(1, Number(units) || 1),
        }),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || 'Warden check failed.');
      await onRefreshState();
      setLastDecision(data.decision as WardenDecision);
      setProbedTier(data.tier as TierCapabilities);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setChecking(false);
    }
  }

  async function handleUpdateCap() {
    setUpdatingCap(true);
    setError(null);
    try {
      const resp = await fetch('/api/natalie/cap', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ hard_cap_usd: Number(hardCapUsd) || 0 }),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || 'Failed to update hard cap.');
      await onRefreshState();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setUpdatingCap(false);
    }
  }

  async function handleApprovalDecision(approvalId: string, decision: 'approved' | 'denied') {
    setError(null);
    try {
      const resp = await fetch('/api/natalie/decide', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approval_id: approvalId, decision, decided_by: 'user' }),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || 'Failed to record approval decision.');
      await onRefreshState();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  const natalie = state.natalie;

  return (
    <div className="space-y-8">
      {/* Startup Free-Tier Capability Probe */}
      <section aria-label="Startup API tier detection" className="bg-white border border-slate-200 rounded-lg p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-xl">
            <h2 className="text-base font-semibold text-slate-900">Startup API Key Tier Probe</h2>
            <p className="text-sm text-slate-600 mt-1">
              {probedTier.pro_credit_note}
            </p>
          </div>
          <div className="text-sm font-mono tabular-nums text-slate-700">
            Detected Tier:{' '}
            <span className={probedTier.tier === 'paid' ? 'font-semibold text-blue-700' : 'font-semibold text-slate-900'}>
              {probedTier.tier.toUpperCase()}
            </span>
            <span className="mx-2 text-slate-300" aria-hidden="true">·</span>
            {probedTier.rpm_limit} RPM / {probedTier.rpd_limit.toLocaleString()} RPD
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-5 pt-5 border-t border-slate-200 text-sm">
          <div>
            <div className="text-xs font-medium text-slate-500">Nano Banana (generate_image)</div>
            <div className="mt-1 font-semibold text-emerald-700">
              {probedTier.image_enabled ? 'Enabled within rate limits' : 'Disabled'}
            </div>
            <div className="text-xs text-slate-500 mt-0.5">Used by Vision via gstudioaimcp</div>
          </div>

          <div>
            <div className="text-xs font-medium text-slate-500">Gemini TTS (generate_speech)</div>
            <div className="mt-1 font-semibold text-emerald-700">
              {probedTier.speech_enabled ? 'Enabled within rate limits' : 'Disabled'}
            </div>
            <div className="text-xs text-slate-500 mt-0.5">Used by Griot via gstudioaimcp</div>
          </div>

          <div>
            <div className="text-xs font-medium text-slate-500">Veo Video (generate_video)</div>
            <div className={`mt-1 font-semibold ${probedTier.video_enabled ? 'text-amber-700' : 'text-red-700'}`}>
              {probedTier.video_enabled ? 'Paid key active (Warden approval required)' : 'Disabled on free-tier key'}
            </div>
            <div className="text-xs text-slate-500 mt-0.5">
              {probedTier.video_enabled ? 'Every clip is billed and previewed first' : 'Prevents runtime BAD_REQUEST failure'}
            </div>
          </div>
        </div>

        {probedTier.warning && (
          <div className="mt-4 p-3.5 bg-amber-50 border border-amber-200 rounded-md text-sm text-amber-900">
            {probedTier.warning}
          </div>
        )}
      </section>

      {/* Warden Preflight Simulator */}
      <section aria-label="Warden spend guardrail simulator" className="bg-white border border-slate-200 rounded-lg p-6">
        <h2 className="text-base font-semibold text-slate-900">Warden Preflight Guardrail</h2>
        <p className="text-sm text-slate-600 mt-0.5">
          Every billed call from Vision or Griot executes cost preview, hard-cap validation, and N.A.T.A.L.I.E. approval routing before invocation.
        </p>

        <form onSubmit={handleWardenCheck} className="mt-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div>
            <label htmlFor="warden-tier" className="block text-xs font-medium text-slate-600 mb-1">
              Simulated API Key Tier
            </label>
            <select
              id="warden-tier"
              value={tierMode}
              onChange={(e) => {
                const next = e.target.value as 'free' | 'paid';
                setTierMode(next);
                setDepositedUsd(next === 'paid' ? '10' : '0');
                if (next === 'paid' && Number(hardCapUsd) === 0) {
                  setHardCapUsd('1.00');
                }
              }}
              className="w-full px-3 py-2 text-sm text-slate-900 bg-white border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-600"
            >
              <option value="free">Free-Tier Key ($0 deposited, Pro plan alone)</option>
              <option value="paid">Paid Key (&gt;=$5 deposited in billing account)</option>
            </select>
          </div>

          <div>
            <label htmlFor="warden-agent" className="block text-xs font-medium text-slate-600 mb-1">
              Calling Subagent
            </label>
            <select
              id="warden-agent"
              value={agent}
              onChange={(e) => setAgent(e.target.value as 'Vision' | 'Griot')}
              className="w-full px-3 py-2 text-sm text-slate-900 bg-white border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-600"
            >
              <option value="Vision">Vision (Images / Video)</option>
              <option value="Griot">Griot (Speech / Storyboards)</option>
            </select>
          </div>

          <div>
            <label htmlFor="warden-tool" className="block text-xs font-medium text-slate-600 mb-1">
              Requested Media MCP Tool
            </label>
            <select
              id="warden-tool"
              value={tool}
              onChange={(e) => setTool(e.target.value as typeof tool)}
              className="w-full px-3 py-2 text-sm text-slate-900 bg-white border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-600"
            >
              <option value="generate_video">generate_video (Veo · $0.35/clip)</option>
              <option value="generate_image">generate_image (Nano Banana · free / $0.03)</option>
              <option value="generate_speech">generate_speech (TTS · free / $0.01)</option>
              <option value="paid_llm_call">paid_llm_call (Heavy billed reasoning · $0.05)</option>
            </select>
          </div>

          <div>
            <label htmlFor="warden-cap" className="block text-xs font-medium text-slate-600 mb-1">
              Hard Cap (USD)
            </label>
            <div className="flex gap-2">
              <input
                id="warden-cap"
                type="number"
                step="0.05"
                min="0"
                value={hardCapUsd}
                onChange={(e) => setHardCapUsd(e.target.value)}
                className="w-full px-3 py-2 text-sm font-mono tabular-nums text-slate-900 bg-white border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-600"
              />
              <button
                type="button"
                onClick={handleUpdateCap}
                disabled={updatingCap}
                className="px-3 py-2 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-md whitespace-nowrap shrink-0 cursor-pointer"
              >
                Save Cap
              </button>
            </div>
          </div>

          <div>
            <label htmlFor="warden-threshold" className="block text-xs font-medium text-slate-600 mb-1">
              Approval Threshold (USD)
            </label>
            <input
              id="warden-threshold"
              type="number"
              step="0.01"
              min="0"
              value={approvalThresholdUsd}
              onChange={(e) => setApprovalThresholdUsd(e.target.value)}
              className="w-full px-3 py-2 text-sm font-mono tabular-nums text-slate-900 bg-white border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
          </div>

          <div>
            <label htmlFor="warden-units" className="block text-xs font-medium text-slate-600 mb-1">
              Units (clips / images / calls)
            </label>
            <div className="flex gap-2">
              <input
                id="warden-units"
                type="number"
                min="1"
                max="20"
                value={units}
                onChange={(e) => setUnits(e.target.value)}
                className="w-24 px-3 py-2 text-sm font-mono tabular-nums text-slate-900 bg-white border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-600"
              />
              <button
                type="submit"
                disabled={checking}
                className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2 min-h-[40px] text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer"
              >
                <ShieldCheck className="w-4 h-4" aria-hidden="true" />
                {checking ? 'Checking...' : 'Run Warden Check'}
              </button>
            </div>
          </div>
        </form>

        {error && (
          <p role="alert" className="mt-3 text-sm text-red-700 font-medium">
            {error}
          </p>
        )}

        {lastDecision && (
          <div className="mt-5 pt-5 border-t border-slate-200" data-testid="warden-decision">
            <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
              <div>
                Verdict:{' '}
                <span
                  className={
                    lastDecision.verdict === 'ALLOW'
                      ? 'font-mono font-bold text-emerald-700'
                      : lastDecision.verdict === 'NEED_APPROVAL'
                        ? 'font-mono font-bold text-amber-700'
                        : 'font-mono font-bold text-red-700'
                  }
                >
                  {lastDecision.verdict}
                </span>
                <span className="mx-2 text-slate-300" aria-hidden="true">·</span>
                <span className="font-mono text-slate-700">{lastDecision.agent}.{lastDecision.tool}</span>
              </div>
              <div className="font-mono text-xs text-slate-600 tabular-nums">
                Preview {formatUsd(lastDecision.estimated_cost_usd)} · Spend {formatUsd(lastDecision.current_spend_usd)} / Cap {formatUsd(lastDecision.hard_cap_usd)}
              </div>
            </div>
            <p className="mt-1.5 text-sm text-slate-700">{lastDecision.reason}</p>
          </div>
        )}
      </section>

      {/* N.A.T.A.L.I.E. Operations Queue & Audit Log */}
      <section aria-label="N.A.T.A.L.I.E. Operations and Approval Queue" className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-slate-900">N.A.T.A.L.I.E. Approval Queue</h2>
              <p className="text-xs text-slate-600 mt-0.5">
                Budget Spent {formatUsd(natalie.spent_usd)} / Hard Cap {formatUsd(natalie.hard_cap_usd)} · Billed Agents:{' '}
                <span className={natalie.billed_agents_frozen ? 'font-semibold text-red-700' : 'font-semibold text-emerald-700'}>
                  {natalie.billed_agents_frozen ? 'Frozen near cap' : 'Active'}
                </span>
              </p>
            </div>
          </div>

          {natalie.approval_queue.length === 0 ? (
            <div className="p-6 text-sm text-slate-500">
              No pending Warden escalations. Trigger a paid-tier Veo or threshold-crossing call above to queue an approval item.
            </div>
          ) : (
            <div className="divide-y divide-slate-200">
              {natalie.approval_queue.map((req) => (
                <div key={req.id} className="p-4 flex flex-col gap-2">
                  <div className="flex items-center justify-between gap-2 text-xs">
                    <span className="font-mono font-semibold text-slate-800">
                      {req.id} · {req.agent}.{req.tool} ({formatUsd(req.estimated_cost_usd)})
                    </span>
                    <span
                      className={
                        req.status === 'approved'
                          ? 'font-semibold text-emerald-700'
                          : req.status === 'denied'
                            ? 'font-semibold text-red-700'
                            : 'font-semibold text-amber-700'
                      }
                    >
                      {req.status.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600">{req.reason}</p>
                  {req.status === 'pending' && (
                    <div className="flex items-center gap-2 pt-1">
                      <button
                        type="button"
                        onClick={() => handleApprovalDecision(req.id, 'approved')}
                        aria-label={`Approve ${req.id}`}
                        className="px-3 py-1.5 text-xs font-medium text-white bg-emerald-700 hover:bg-emerald-800 rounded-md cursor-pointer whitespace-nowrap"
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        onClick={() => handleApprovalDecision(req.id, 'denied')}
                        aria-label={`Deny ${req.id}`}
                        className="px-3 py-1.5 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-md cursor-pointer whitespace-nowrap"
                      >
                        Deny
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-200">
            <h2 className="text-base font-semibold text-slate-900">Operations Audit Log (ops_audit.ndjson)</h2>
            <p className="text-xs text-slate-600 mt-0.5">
              N.A.T.A.L.I.E. writes structured operational logs and escalations only—never code.
            </p>
          </div>
          {natalie.audit_log.length === 0 ? (
            <div className="p-6 text-sm text-slate-500">
              No operational events recorded yet. Run a Warden check or Dream preview to populate the audit log.
            </div>
          ) : (
            <div className="divide-y divide-slate-200 max-h-80 overflow-y-auto">
              {natalie.audit_log.map((entry, idx) => (
                <div key={`${entry.ts}-${idx}`} className="p-3.5 text-xs">
                  <div className="flex items-center justify-between gap-2 font-mono">
                    <span className="font-semibold text-slate-900">{entry.event}</span>
                    <span className="text-slate-500 tabular-nums">{entry.ts.slice(11, 19)} UTC</span>
                  </div>
                  <div className="mt-1 font-mono text-slate-600 break-all">
                    {JSON.stringify(entry.details)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
