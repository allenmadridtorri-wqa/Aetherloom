export type NavTab =
  | 'orchestrator'
  | 'safety'
  | 'memory'
  | 'adapters'
  | 'source';

export interface TierCapabilities {
  tier: 'free' | 'paid';
  default_model: string;
  rpm_limit: number;
  rpd_limit: number;
  image_enabled: boolean;
  speech_enabled: boolean;
  video_enabled: boolean;
  warning: string | null;
  pro_credit_note: string;
}

export interface MeterSummary {
  record_count: number;
  input_tokens: number;
  output_tokens: number;
  cached_tokens: number;
  cost_usd: number;
  pass_rate: number;
  pass_rate_change_pct: number;
  memory_turn_input_savings_pct: number;
  overall_task_savings_pct: number;
  accuracy_regression: boolean;
  recommended_strategy: 'standard' | 'conservative';
}

export interface MeterRecord {
  task_id: string;
  agent: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  cached_tokens: number;
  cost_usd: number;
  pass_rate: number;
  mode: 'swarm' | 'teamwork' | 'hybrid';
  timestamp: string;
}

export interface ApprovalRequest {
  id: string;
  agent: string;
  tool: string;
  estimated_cost_usd: number;
  reason: string;
  status: 'pending' | 'approved' | 'denied';
  created_at: string;
  decided_by?: string | null;
  decided_at?: string | null;
}

export interface AuditLogEntry {
  ts: string;
  actor: string;
  event: string;
  details: Record<string, unknown>;
}

export interface NatalieSnapshot {
  spent_usd: number;
  hard_cap_usd: number;
  billed_agents_frozen: boolean;
  approval_queue: ApprovalRequest[];
  audit_log: AuditLogEntry[];
}

export interface MemoryNote {
  id: number;
  project: string;
  body: string;
}

export interface CodeMapEntry {
  id: number;
  path: string;
  symbol: string;
  summary: string;
}

export interface SessionEntry {
  id: string;
  ts: string;
  summary: string;
  raw_ref: string;
}

export interface MemorySearchHit {
  source: 'notes' | 'code_map' | 'sessions';
  id: string;
  title: string;
  content: string;
  bm25: number;
  tokens: number;
}

export interface MemorySearchResult {
  query: string;
  k: number;
  tokens_used: number;
  budget_tokens: number;
  hits: MemorySearchHit[];
}

export interface DreamGate {
  eligible: boolean;
  hours_elapsed: number;
  min_hours_required: number;
  sessions_since_last: number;
  min_sessions_required: number;
}

export interface DreamDiffRecord {
  id: string;
  ts: string;
  patch_path: string;
  status: 'pending' | 'approved' | 'rejected' | 'applied';
  approved_by?: string | null;
  approved_at?: string | null;
  patch_content?: string;
}

export interface SkillRecord {
  id: string;
  name: string;
  path: string;
  status: 'core' | 'candidate' | 'promoted' | 'rejected' | 'downgraded';
  benchmark_score?: number | null;
  promoted_at?: string | null;
}

export interface WorkbenchState {
  tier: TierCapabilities;
  meter_summary: MeterSummary;
  meter_records: MeterRecord[];
  natalie: NatalieSnapshot;
  notes: MemoryNote[];
  code_map: CodeMapEntry[];
  sessions: SessionEntry[];
  dream_gate: DreamGate;
  dream_diffs: DreamDiffRecord[];
  skills: SkillRecord[];
}

export interface RouteDecision {
  mode: 'swarm' | 'teamwork' | 'hybrid';
  strategy: 'standard' | 'conservative';
  swarm_signals: string[];
  teamwork_signals: string[];
  active_agents: string[];
  model_assignments: Record<string, string>;
  context_budget_tokens: number;
  prompt_prefix_caching: boolean;
  compress_relevant_context: boolean;
  rationale: string;
}

export interface WardenDecision {
  verdict: 'ALLOW' | 'DENY' | 'NEED_APPROVAL';
  agent: string;
  tool: string;
  estimated_cost_usd: number;
  current_spend_usd: number;
  hard_cap_usd: number;
  reason: string;
  approval_id?: string | null;
}

export interface OrchestrationResult {
  run_id: string;
  goal: string;
  mode: 'swarm' | 'teamwork' | 'hybrid';
  strategy: 'standard' | 'conservative';
  status: 'completed' | 'paused';
  blockers: string[];
  next_step: string;
  board_path: string;
  route: RouteDecision;
  memory: MemorySearchResult;
  warden: WardenDecision | null;
  meter_record: MeterRecord;
  meter_summary: MeterSummary;
  board_events: Array<Record<string, unknown>>;
  tier: TierCapabilities;
}

export interface PluginFileEntry {
  path: string;
  category: 'canonical' | 'skills' | 'agents' | 'core' | 'benchmarks' | 'adapters' | 'tests' | 'docs';
  role: string;
  sizeBytes: number;
  lines: number;
  content: string;
}

export interface AcceptanceTestItem {
  id: string;
  title: string;
  passed: boolean;
  error: string | null;
}

export interface AcceptanceReport {
  total: number;
  passed: number;
  failed: number;
  all_passed: boolean;
  tests: AcceptanceTestItem[];
}
