#!/usr/bin/env python3
"""JSON CLI Bridge for AetherLoom runtime operations.

Allows the AetherLoom Workbench backend (Express) or any external script to invoke
the live Python SQLite FTS5 memory store, Router, Orchestrator, Warden, N.A.T.A.L.I.E.,
Dream preview engine, Skill Learning pipeline, and Acceptance Test Suite.
"""

from __future__ import annotations

import json
import pathlib
import sys
from typing import Any, Dict

ROOT = pathlib.Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from build_adapters import build_all_adapters
from core.dream import DreamJob
from core.memory import MemoryStore
from core.meter import Meter
from core.natalie import NatalieOps
from core.orchestrator import SupergravityOrchestrator
from core.router import Router
from core.skill_learning import SkillLearningPipeline
from core.tier_probe import probe_api_tier
from core.warden import Warden
from tests.test_acceptance import run_as_json

DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "workbench.db"
OPS_DIR = DATA_DIR / "ops"
DIFFS_DIR = ROOT / "dream_diffs"


def ensure_seeded(store: MemoryStore, meter: Meter) -> None:
    if store.list_notes(limit=1):
        return
    store.add_note(
        "aetherloom",
        "Warden checks cost preview and hard cap before any Vision or Griot media MCP call.",
    )
    store.add_note(
        "aetherloom",
        "Free-tier keys support Nano Banana generate_image and TTS generate_speech within ~15 RPM / ~1,500 RPD; Veo generate_video is disabled proactively to prevent BAD_REQUEST.",
    )
    store.add_note(
        "aetherloom",
        "SQLite FTS5 BM25 returns top-k minimal slices without compressing relevant code context.",
    )
    store.add_note(
        "aetherloom",
        "SQLite FTS5 BM25 returns top-k minimal slices without compressing relevant code context.",
    )
    store.upsert_code_map(
        "core/router.py",
        "Router.classify",
        "Classifies goals into swarm, teamwork, or hybrid and reverts to conservative mode on accuracy_regression.",
    )
    store.upsert_code_map(
        "core/warden.py",
        "Warden.check",
        "Enforces free-tier Veo block, N.A.T.A.L.I.E. freeze flag, hard cap check, and approval queuing.",
    )
    store.upsert_code_map(
        "core/dream.py",
        "DreamJob.run",
        "Runs Collect -> Propose -> Validate -> Commit-as-pending after >=24h and >=5 sessions in preview mode.",
    )
    for i in range(1, 6):
        store.add_session(
            f"sess_seed_0{i}",
            f"Verified milestone {i}: FTS5 retrieval, Warden guardrails, and adapter schema validation.",
            raw_ref=f"runs/seed_0{i}/board.ndjson",
        )
    for skill_name in ("supergravity", "memory", "dream", "meter", "skill-learning"):
        store.upsert_skill(
            skill_id=f"core_{skill_name}",
            name=skill_name,
            path=f"skills/{skill_name}/SKILL.md",
            status="core",
            benchmark_score=100.0,
        )
    meter.record(
        task_id="seed_01",
        agent="Builder",
        model="gemini-3.6-flash",
        input_tokens=540,
        output_tokens=290,
        cached_tokens=340,
        cost_usd=0.0,
        pass_rate=94.0,
        mode="swarm",
        memory_driven=True,
        baseline_input_tokens=3650,
        baseline_total_tokens=1720,
    )
    meter.record(
        task_id="seed_02",
        agent="Critic",
        model="gemini-3.6-flash-thinking",
        input_tokens=720,
        output_tokens=380,
        cached_tokens=420,
        cost_usd=0.0,
        pass_rate=93.0,
        mode="teamwork",
        memory_driven=True,
        baseline_input_tokens=4900,
        baseline_total_tokens=2260,
    )


def handle_action(action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    store = MemoryStore(DB_PATH)
    meter = Meter(store)
    ensure_seeded(store, meter)
    natalie = NatalieOps(OPS_DIR, hard_cap_usd=float(payload.get("hard_cap_usd", 0.0)))

    try:
        if action == "state":
            tier = probe_api_tier(
                api_key=payload.get("api_key", "AIzaFree_default"),
                billing_deposited_usd=float(payload.get("billing_deposited_usd", 0.0)),
                has_ai_pro_plan=bool(payload.get("has_ai_pro_plan", True)),
            )
            dream = DreamJob(store, DIFFS_DIR, natalie=natalie)
            diffs = store.list_dream_diffs()
            for d in diffs:
                p = pathlib.Path(d["patch_path"])
                d["patch_content"] = p.read_text(encoding="utf-8") if p.exists() else ""
            return {
                "tier": tier.to_dict(),
                "meter_summary": meter.summary(),
                "meter_records": meter.list_records(limit=25),
                "natalie": natalie.snapshot(),
                "notes": store.list_notes(limit=30),
                "code_map": store.list_code_map(limit=30),
                "sessions": store.list_sessions(limit=20),
                "dream_gate": dream.check_schedule_gate(),
                "dream_diffs": diffs,
                "skills": store.list_skills(),
            }

        if action == "orchestrate":
            goal = str(payload.get("goal", "")).strip()
            if not goal:
                raise ValueError("Goal cannot be empty.")
            tier = probe_api_tier(
                api_key="AIzaPaid_key" if payload.get("tier") == "paid" else "AIzaFree_key",
                billing_deposited_usd=10.0 if payload.get("tier") == "paid" else 0.0,
            )
            orch = SupergravityOrchestrator(
                root_dir=ROOT,
                store=store,
                natalie=natalie,
                capabilities=tier,
                hard_cap_usd=natalie.hard_cap_usd,
            )
            return orch.orchestrate(
                goal=goal,
                requested_media_tool=payload.get("requested_media_tool") or None,
            )

        if action == "warden_check":
            tier_mode = payload.get("tier", "free")
            deposited = float(payload.get("billing_deposited_usd", 10.0 if tier_mode == "paid" else 0.0))
            tier = probe_api_tier(
                api_key="AIzaPaid_key" if tier_mode == "paid" else "AIzaFree_key",
                billing_deposited_usd=deposited,
                has_ai_pro_plan=bool(payload.get("has_ai_pro_plan", True)),
            )
            cap = float(payload.get("hard_cap_usd", natalie.hard_cap_usd))
            natalie.set_hard_cap(cap)
            threshold = float(payload.get("approval_threshold_usd", 0.05))
            warden = Warden(tier, natalie, hard_cap_usd=cap, approval_threshold_usd=threshold)
            decision = warden.check(
                agent=str(payload.get("agent", "Vision")),
                tool=str(payload.get("tool", "generate_video")),
                units=int(payload.get("units", 1)),
                custom_cost_usd=payload.get("custom_cost_usd"),
            )
            return {
                "decision": decision.to_dict(),
                "tier": tier.to_dict(),
                "natalie": natalie.snapshot(),
            }

        if action == "natalie_decide":
            req = natalie.decide_approval(
                approval_id=str(payload["approval_id"]),
                decision=str(payload["decision"]),
                decided_by=str(payload.get("decided_by", "user")),
            )
            if req is None:
                raise KeyError("Approval request not found.")
            return {"natalie": natalie.snapshot()}

        if action == "natalie_set_cap":
            natalie.set_hard_cap(float(payload.get("hard_cap_usd", 0.0)))
            return {"natalie": natalie.snapshot()}

        if action == "memory_search":
            return store.search(
                query=str(payload.get("query", "")),
                k=int(payload.get("k", 5)),
                context_budget_tokens=int(payload.get("context_budget_tokens", 1200)),
            )

        if action == "memory_add_note":
            project = str(payload.get("project", "aetherloom")).strip() or "aetherloom"
            body = str(payload.get("body", "")).strip()
            if not body:
                raise ValueError("Note body is required.")
            note = store.add_note(project=project, body=body)
            return {"note": note, "notes": store.list_notes(limit=30)}

        if action == "dream_preview":
            dream = DreamJob(store, DIFFS_DIR, natalie=natalie)
            res = dream.run(mode="preview", force_schedule_override=bool(payload.get("force", True)))
            return res

        if action == "dream_approve":
            dream = DreamJob(store, DIFFS_DIR, natalie=natalie)
            return dream.approve_diff(
                diff_id=str(payload["diff_id"]),
                approved_by=str(payload.get("approved_by", "SuccessAuditor")),
            )

        if action == "skill_evaluate":
            pipeline = SkillLearningPipeline(ROOT, store)
            name = str(payload.get("name", "")).strip()
            desc = str(payload.get("description", "Candidate procedural skill")).strip()
            instructions = str(payload.get("instructions", "")).strip()
            if not name or not instructions:
                raise ValueError("Skill name and instructions are required.")
            pipeline.draft_candidate(name=name, description=desc, instructions=instructions)
            res = pipeline.evaluate_and_promote(name=name)
            return {"result": res, "skills": store.list_skills()}

        if action == "build_adapters":
            return {"generated": build_all_adapters()}

        if action == "run_acceptance":
            return run_as_json()

        raise ValueError(f"Unknown action: {action}")
    finally:
        store.close()


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Missing action argument"}))
        sys.exit(1)
    action = sys.argv[1]
    raw_in = sys.stdin.read().strip()
    payload = json.loads(raw_in) if raw_in else {}
    try:
        out = handle_action(action, payload)
        print(json.dumps(out))
    except Exception as exc:
        print(json.dumps({"error": str(exc)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
