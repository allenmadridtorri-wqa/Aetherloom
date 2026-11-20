import type { MeterSummary, PluginFileEntry } from '../types';

export interface AgentMeta {
  id: string;
  name: string;
  layer: 'L0' | 'L1' | 'L2' | 'L3' | 'L4';
  layerName: string;
  responsibility: string;
  billed?: boolean;
}

export const AGENT_ROSTER: AgentMeta[] = [
  { id: 'commander', name: 'Commander', layer: 'L0', layerName: 'Command', responsibility: 'Receive goal, route via Router, aggregate, report briefly. No direct writes.' },
  { id: 'builder', name: 'Builder', layer: 'L1', layerName: 'Build', responsibility: 'Write code inside isolated git worktrees.' },
  { id: 'tester', name: 'Tester', layer: 'L1', layerName: 'Build', responsibility: 'Run tests after every edit; return verbatim command output.' },
  { id: 'refactorer', name: 'Refactorer', layer: 'L1', layerName: 'Build', responsibility: 'Restructure code strictly without behavior change.' },
  { id: 'scout', name: 'Scout', layer: 'L2', layerName: 'Research', responsibility: 'Inspect docs, web, and free-tier YouTube transcripts; return short cited notes.' },
  { id: 'codemapper', name: 'CodeMapper', layer: 'L2', layerName: 'Research', responsibility: 'Maintain and query SQLite FTS5 code map; return smallest relevant slice.' },
  { id: 'docminer', name: 'DocMiner', layer: 'L2', layerName: 'Research', responsibility: 'Extract hard constraints and interfaces from long documents.' },
  { id: 'adversary', name: 'Adversary', layer: 'L3', layerName: 'Quality', responsibility: 'Attack live diffs for defects; review-only, zero write authority.' },
  { id: 'critic', name: 'Critic', layer: 'L3', layerName: 'Quality', responsibility: 'Independent review of correctness, robustness, and maintainability.' },
  { id: 'challenger', name: 'Challenger', layer: 'L3', layerName: 'Quality', responsibility: 'Author adversarial test suites, edge cases, and failure paths.' },
  { id: 'auditor', name: 'Auditor', layer: 'L3', layerName: 'Quality', responsibility: 'Verify evidence is real command output, never mocks or skipped tests.' },
  { id: 'success_auditor', name: 'SuccessAuditor', layer: 'L3', layerName: 'Quality', responsibility: 'Final end-to-end verification gate; approve or reject the entire task.' },
  { id: 'vision', name: 'Vision', layer: 'L4', layerName: 'Creative + Ops', responsibility: 'Generate images, UI, and brand assets via media MCP through Warden.', billed: true },
  { id: 'griot', name: 'Griot', layer: 'L4', layerName: 'Creative + Ops', responsibility: 'Author scripts, copy, and video storyboards via media MCP through Warden.', billed: true },
  { id: 'natalie', name: 'N.A.T.A.L.I.E.', layer: 'L4', layerName: 'Creative + Ops', responsibility: 'Operations & Scheduling: cron triggers, budget ledger, approval queue, audit log. Not a coder.' },
  { id: 'archivist', name: 'Archivist', layer: 'L4', layerName: 'Creative + Ops', responsibility: 'SQLite FTS5 memory read/write, task log, and code-map maintenance.' },
  { id: 'router', name: 'Router', layer: 'L4', layerName: 'Creative + Ops', responsibility: 'Mode classification and accuracy-preserving model/token routing.' },
  { id: 'warden', name: 'Warden', layer: 'L4', layerName: 'Creative + Ops', responsibility: 'Spend and permission guardrail: cost preview -> hard cap -> approval.' },
];

export interface HostAdapterSpec {
  id: string;
  name: string;
  paradigm: string;
  installCommand: string;
  keyFacts: string;
  pathPrefix: string;
}

export const HOST_ADAPTER_SPECS: HostAdapterSpec[] = [
  {
    id: 'antigravity',
    name: 'Antigravity',
    paradigm: 'MCP-only + .agents/ + environment hooks',
    installCommand: 'python3 aetherloom/install.py --target antigravity-global',
    keyFacts: 'Supports dynamic subagents, N.A.T.A.L.I.E. scheduled background tasks, and pre-execution Warden environment hooks. Also supports --target antigravity-workspace.',
    pathPrefix: 'adapters/antigravity/',
  },
  {
    id: 'claude-code',
    name: 'Claude Code',
    paradigm: 'plugin.json + commands + 18 agents + JSON hooks',
    installCommand: 'python3 aetherloom/install.py --target claude-code --workspace .',
    keyFacts: 'Ships plugin.json, commands/supergravity.md, all 18 agents/*.md, .mcp.json, and PreToolUse JSON stdin/stdout Warden hook.',
    pathPrefix: 'adapters/claude-code/',
  },
  {
    id: 'cursor',
    name: 'Cursor',
    paradigm: '.cursor/mcp.json + .cursor/rules/*.mdc',
    installCommand: 'python3 aetherloom/install.py --target cursor --workspace .',
    keyFacts: 'Wires AetherLoom, YouTube transcript, and Gemini media MCP servers alongside always-apply orchestration rules.',
    pathPrefix: 'adapters/cursor/',
  },
  {
    id: 'gemini-cli',
    name: 'Gemini CLI',
    paradigm: '~/.gemini/settings.json + BeforeTool/AfterTool hooks',
    installCommand: 'python3 aetherloom/install.py --target gemini-cli',
    keyFacts: 'Configures Gemini 3.6 Flash free-tier default model and BeforeTool/AfterTool JSON stdin/stdout hooks.',
    pathPrefix: 'adapters/gemini-cli/',
  },
  {
    id: 'codex-cli',
    name: 'Codex CLI',
    paradigm: '~/.codex/hooks.json + ~/.codex/config.toml',
    installCommand: 'python3 aetherloom/install.py --target codex-cli',
    keyFacts: 'Registers MCP server stanzas in TOML and pre-tool Warden guardrails via JSON stdin/stdout hooks.',
    pathPrefix: 'adapters/codex-cli/',
  },
  {
    id: 'generic-mcp',
    name: 'Generic MCP / VS Code',
    paradigm: 'Standalone JSON-RPC 2.0 stdio MCP server + .vscode/mcp.json',
    installCommand: 'python3 aetherloom/install.py --target vscode --workspace .',
    keyFacts: 'Works in VS Code (Copilot + Antigravity extension), OpenCode, Windsurf, and any MCP host exposing memory.search, meter.record, warden.check, router.classify, supergravity.orchestrate.',
    pathPrefix: 'adapters/generic-mcp/',
  },
];

export function describePluginFileRole(relPath: string): {
  category: PluginFileEntry['category'];
  role: string;
} {
  if (relPath === 'manifest.json') {
    return { category: 'canonical', role: 'Canonical plugin manifest defining 18 agents, 5 core skills, free-tier policy, and adapter targets.' };
  }
  if (relPath === 'AGENTS.md') {
    return { category: 'canonical', role: 'Root canonical constitution governing all 5 layers, safety rails, and honesty invariants.' };
  }
  if (relPath === 'build_adapters.py') {
    return { category: 'canonical', role: 'Deterministic generator that compiles all 6 host-specific adapters from canonical source.' };
  }
  if (relPath === 'install.py') {
    return { category: 'canonical', role: 'Cross-platform zero-dependency installer for Antigravity IDE, VS Code, Claude Code, Cursor, Gemini CLI, and Codex CLI.' };
  }
  if (relPath === '.gitignore') {
    return { category: 'canonical', role: 'GitHub-ready ignore rules excluding runtime SQLite DB, runs, and Python caches.' };
  }
  if (relPath === 'cli_bridge.py') {
    return { category: 'core', role: 'JSON stdin/stdout CLI bridge exposing live Python runtime modules to external tools and UI.' };
  }
  if (relPath === 'README.md') {
    return { category: 'docs', role: 'Complete documentation with zero-edit installation steps per host and free-tier billing caveats.' };
  }
  if (relPath.startsWith('skills/')) {
    const name = relPath.split('/')[1] || 'skill';
    const roles: Record<string, string> = {
      supergravity: 'Core immutable /supergravity orchestration skill defining swarm, teamwork, and hybrid execution.',
      memory: 'Core immutable Archivist skill for SQLite FTS5 BM25 retrieval and context-budget slicing.',
      dream: 'Core immutable four-phase propose-then-commit Dream memory consolidation specification.',
      meter: 'Core immutable Meter telemetry skill separating memory-turn savings, overall savings, and pass rate.',
      'skill-learning': 'Core immutable benchmark-gated skill promotion specification protecting hand-written skills.',
      candidates: 'Unpromoted candidate skill generated from a task trajectory awaiting benchmark evaluation.',
      learned: 'Benchmark-promoted learned skill verified against >=5 tasks without overwriting core skills.',
    };
    return { category: 'skills', role: roles[name] || `Skill specification file (${relPath}).` };
  }
  if (relPath.startsWith('agents/')) {
    const id = relPath.replace('agents/', '').replace('.md', '');
    const meta = AGENT_ROSTER.find((a) => a.id === id);
    return {
      category: 'agents',
      role: meta
        ? `${meta.layer} ${meta.name} subagent specification — ${meta.responsibility}`
        : `Subagent definition (${id}).`,
    };
  }
  if (relPath.startsWith('core/')) {
    const map: Record<string, string> = {
      'core/__init__.py': 'Python package marker for AetherLoom core runtime modules.',
      'core/schema.sql': 'SQLite schema with sessions, tasks, skills, code_map, notes, dream_diffs, and FTS5 BM25 virtual tables.',
      'core/memory.py': 'Archivist SQLite FTS5 BM25 engine performing top-k context-budget retrieval without lossy compression.',
      'core/meter.py': 'Meter telemetry recorder calculating memory-turn savings, overall savings, and accuracy regression.',
      'core/tier_probe.py': 'Startup API key tier detector disabling Veo on free-tier keys with a clear warning.',
      'core/natalie.py': 'N.A.T.A.L.I.E. operations controller owning budget ledger, freeze flag, approval queue, and ops audit log.',
      'core/warden.py': 'Warden spend guardrail executing cost preview, hard-cap enforcement, and ALLOW/DENY/NEED_APPROVAL decisions.',
      'core/router.py': 'Router mode classifier (swarm/teamwork/hybrid) with accuracy-preserving model tier assignment.',
      'core/dream.py': 'Dream four-phase consolidation job (Collect -> Propose -> Validate -> Commit-as-pending) defaulting to preview.',
      'core/skill_learning.py': 'Skill learning pipeline writing candidates, running benchmarks, and promoting only to skills/learned/.',
      'core/orchestrator.py': 'Commander /supergravity runtime writing append-only runs/<id>/board.ndjson traces.',
    };
    return { category: 'core', role: map[relPath] || 'Core Python runtime module.' };
  }
  if (relPath.startsWith('benchmarks/')) {
    if (relPath.endsWith('tasks.json')) {
      return { category: 'benchmarks', role: 'Deterministic 6-task benchmark suite (>=5 required) with no-skill baseline metrics.' };
    }
    if (relPath.endsWith('runner.py')) {
      return { category: 'benchmarks', role: 'Objective benchmark harness comparing candidate skills against baseline pass rate and tokens.' };
    }
    return { category: 'benchmarks', role: 'Python package initializer for benchmark harness.' };
  }
  if (relPath.startsWith('adapters/')) {
    const host = relPath.split('/')[1] || 'host';
    return {
      category: 'adapters',
      role: `Generated ${host} host adapter artifact compiled automatically from canonical source.`,
    };
  }
  if (relPath.startsWith('tests/')) {
    return {
      category: 'tests',
      role: 'Executable 10-check acceptance test suite validating all AetherLoom invariants and adapters.',
    };
  }
  return { category: 'docs', role: 'Plugin supporting file.' };
}

export function filterPluginFiles(
  files: PluginFileEntry[],
  query: string,
  category: string,
): PluginFileEntry[] {
  const q = query.trim().toLowerCase();
  return files.filter((file) => {
    const matchesCat = category === 'all' || file.category === category;
    if (!matchesCat) return false;
    if (!q) return true;
    return (
      file.path.toLowerCase().includes(q) ||
      file.role.toLowerCase().includes(q)
    );
  });
}

export function evaluateMeterHealth(summary: MeterSummary): {
  memorySavingsOnTarget: boolean;
  overallSavingsOnTarget: boolean;
  passRateHealthy: boolean;
} {
  return {
    memorySavingsOnTarget: summary.memory_turn_input_savings_pct >= 75,
    overallSavingsOnTarget:
      summary.overall_task_savings_pct >= 40 && summary.overall_task_savings_pct <= 70,
    passRateHealthy: summary.pass_rate >= 90 && !summary.accuracy_regression,
  };
}

export function formatUsd(amount: number): string {
  return `$${Number.isFinite(amount) ? amount.toFixed(2) : '0.00'}`;
}

export function formatPct(value: number): string {
  return `${Number.isFinite(value) ? value.toFixed(1) : '0.0'}%`;
}
