import test from 'node:test';
import assert from 'node:assert/strict';
import {
  AGENT_ROSTER,
  HOST_ADAPTER_SPECS,
  describePluginFileRole,
  evaluateMeterHealth,
  filterPluginFiles,
  formatPct,
  formatUsd,
} from './aetherloomLogic';
import type { PluginFileEntry } from '../types';

test('agent roster defines exactly 18 subagents across 5 layers', () => {
  assert.equal(AGENT_ROSTER.length, 18);
  const layers = new Set(AGENT_ROSTER.map((a) => a.layer));
  assert.deepEqual([...layers].sort(), ['L0', 'L1', 'L2', 'L3', 'L4']);
  const billedIds = AGENT_ROSTER.filter((a) => a.billed).map((a) => a.id).sort();
  assert.deepEqual(billedIds, ['griot', 'vision']);
});

test('host adapter catalog covers all 6 required host targets', () => {
  assert.equal(HOST_ADAPTER_SPECS.length, 6);
  const ids = HOST_ADAPTER_SPECS.map((h) => h.id);
  assert.deepEqual(ids, [
    'antigravity',
    'claude-code',
    'cursor',
    'gemini-cli',
    'codex-cli',
    'generic-mcp',
  ]);
});

test('describePluginFileRole categorizes canonical, core, skills, agents, and adapters accurately', () => {
  assert.equal(describePluginFileRole('manifest.json').category, 'canonical');
  assert.equal(describePluginFileRole('core/warden.py').category, 'core');
  assert.equal(describePluginFileRole('skills/supergravity/SKILL.md').category, 'skills');
  assert.equal(describePluginFileRole('agents/natalie.md').category, 'agents');
  assert.equal(describePluginFileRole('adapters/antigravity/.agents/AGENTS.md').category, 'adapters');
  assert.equal(describePluginFileRole('tests/test_acceptance.py').category, 'tests');
});

test('filterPluginFiles filters by category and case-insensitive search query', () => {
  const sample: PluginFileEntry[] = [
    { path: 'manifest.json', category: 'canonical', role: 'Canonical manifest', sizeBytes: 100, lines: 10, content: '{}' },
    { path: 'core/warden.py', category: 'core', role: 'Warden spend guardrail', sizeBytes: 200, lines: 20, content: '' },
    { path: 'adapters/cursor/.cursor/mcp.json', category: 'adapters', role: 'Generated cursor adapter', sizeBytes: 150, lines: 12, content: '' },
  ];

  assert.equal(filterPluginFiles(sample, '', 'all').length, 3);
  assert.equal(filterPluginFiles(sample, '', 'core').length, 1);
  assert.equal(filterPluginFiles(sample, 'warden', 'all').length, 1);
  assert.equal(filterPluginFiles(sample, 'cursor', 'core').length, 0);
});

test('evaluateMeterHealth flags healthy targets vs accuracy regression', () => {
  const healthy = evaluateMeterHealth({
    record_count: 4,
    input_tokens: 2000,
    output_tokens: 900,
    cached_tokens: 1200,
    cost_usd: 0,
    pass_rate: 93.5,
    pass_rate_change_pct: 1.5,
    memory_turn_input_savings_pct: 85.2,
    overall_task_savings_pct: 52.0,
    accuracy_regression: false,
    recommended_strategy: 'standard',
  });
  assert.equal(healthy.memorySavingsOnTarget, true);
  assert.equal(healthy.overallSavingsOnTarget, true);
  assert.equal(healthy.passRateHealthy, true);

  const regressed = evaluateMeterHealth({
    record_count: 4,
    input_tokens: 2000,
    output_tokens: 900,
    cached_tokens: 1200,
    cost_usd: 0,
    pass_rate: 84.0,
    pass_rate_change_pct: -8.0,
    memory_turn_input_savings_pct: 85.0,
    overall_task_savings_pct: 55.0,
    accuracy_regression: true,
    recommended_strategy: 'conservative',
  });
  assert.equal(regressed.passRateHealthy, false);
});

test('formatters emit consistent tabular currency and percentage strings', () => {
  assert.equal(formatUsd(0.35), '$0.35');
  assert.equal(formatUsd(0), '$0.00');
  assert.equal(formatPct(85.24), '85.2%');
});
