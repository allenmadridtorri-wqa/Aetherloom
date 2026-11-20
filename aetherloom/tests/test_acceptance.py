#!/usr/bin/env python3
"""Acceptance Test Suite for AetherLoom (/supergravity).

Verifies all 10 non-negotiable acceptance criteria directly against the real plugin source,
SQLite FTS5 engine, Router, Dream, Meter, Warden, Free-Tier Probe, and generated adapters.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from build_adapters import build_all_adapters
from core.dream import DreamJob
from core.memory import MemoryStore
from core.meter import Meter
from core.natalie import NatalieOps
from core.router import Router
from core.skill_learning import SkillLearningPipeline
from core.tier_probe import probe_api_tier
from core.warden import Warden


SENTIENCE_PATTERNS = [
    r"\bis sentient\b",
    r"\bis conscious\b",
    r"\bfeels emotions\b",
    r"\bhas consciousness\b",
    r"\btruly alive\b",
    r"\bself-aware being\b",
]


class TestAetherLoomAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generated = build_all_adapters()

    def test_01_multi_host_install_without_manual_edits(self) -> None:
        """1. Installs and runs in Antigravity, Claude Code, and Cursor/Generic MCP without manual edits."""
        ag_agents = ROOT / "adapters/antigravity/.agents/AGENTS.md"
        ag_mcp = ROOT / "adapters/antigravity/.agents/mcp_config.json"
        cc_plugin = ROOT / "adapters/claude-code/plugin.json"
        cc_cmd = ROOT / "adapters/claude-code/commands/supergravity.md"
        cursor_mcp = ROOT / "adapters/cursor/.cursor/mcp.json"
        cursor_rules = ROOT / "adapters/cursor/.cursor/rules/aetherloom.mdc"

        for path in (ag_agents, ag_mcp, cc_plugin, cc_cmd, cursor_mcp, cursor_rules):
            self.assertTrue(path.exists(), f"Missing generated file: {path}")

        # Validate JSON structure and agent count (18 agents)
        cc_data = json.loads(cc_plugin.read_text(encoding="utf-8"))
        self.assertEqual(len(cc_data["agents"]), 18)
        self.assertIn("aetherloom", json.loads(ag_mcp.read_text(encoding="utf-8"))["mcpServers"])
        self.assertIn("aetherloom", json.loads(cursor_mcp.read_text(encoding="utf-8"))["mcpServers"])

        # Exercise Generic MCP server JSON-RPC tools/list and router.classify directly
        sys.path.insert(0, str(ROOT / "adapters/generic-mcp"))
        import server as mcp_server  # type: ignore

        with tempfile.TemporaryDirectory() as tmp:
            srv = mcp_server.AetherLoomMCPServer(data_dir=pathlib.Path(tmp))
            tools_resp = srv.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
            tool_names = {t["name"] for t in tools_resp["result"]["tools"]}
            self.assertEqual(
                tool_names,
                {
                    "memory.search",
                    "meter.record",
                    "warden.check",
                    "router.classify",
                    "supergravity.orchestrate",
                },
            )
            srv.store.close()

    def test_02_router_modes_swarm_teamwork_hybrid(self) -> None:
        """2. /supergravity routes multi-file refactor -> swarm, multi-day research -> teamwork, mixed -> hybrid."""
        router = Router()
        r_swarm = router.classify("Multi-file refactor to rename auth helpers across modules")
        r_teamwork = router.classify("Multi-day deep dive research and audit on SQLite FTS5 indexing architecture")
        r_hybrid = router.classify("Multi-day research and parallel multi-file refactor with milestone verification")

        self.assertEqual(r_swarm.mode, "swarm")
        self.assertEqual(r_teamwork.mode, "teamwork")
        self.assertEqual(r_hybrid.mode, "hybrid")
        self.assertFalse(r_swarm.compress_relevant_context)

    def test_03_memory_fts5_bm25_write_and_retrieve(self) -> None:
        """3. Memory writes and retrieves via SQLite FTS5 BM25 ranking."""
        store = MemoryStore(":memory:")
        store.add_note("aetherloom", "Warden enforces hard cap spend limits before media calls.")
        store.add_note("aetherloom", "SQLite FTS5 BM25 retrieves top-k slices without compressing context.")
        store.upsert_code_map("core/warden.py", "Warden.check", "Preflight spend check and hard cap gate.")
        store.add_session("s_01", "Audited FTS5 BM25 retrieval accuracy across code slices.")

        res = store.search("FTS5 BM25 slices", k=5, context_budget_tokens=800)
        self.assertGreaterEqual(len(res["hits"]), 2)
        self.assertLessEqual(res["tokens_used"], 800)
        # BM25 scores must be ordered ascending (more negative = stronger match)
        scores = [h["bm25"] for h in res["hits"]]
        self.assertEqual(scores, sorted(scores))
        store.close()

    def test_04_dream_preview_diff_no_auto_commit(self) -> None:
        """4. Dream produces a diff and exits in preview mode; nothing is committed automatically."""
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryStore(pathlib.Path(tmp) / "mem.db")
            natalie = NatalieOps(pathlib.Path(tmp) / "ops")
            for i in range(6):
                store.add_session(f"sess_{i}", f"Completed milestone {i} verification")
            store.add_note("aetherloom", "Keep relevant code slices intact.")
            store.add_note("aetherloom", "Keep relevant code slices intact.")  # duplicate to consolidate

            notes_before = store.list_notes()
            dream = DreamJob(store, pathlib.Path(tmp) / "dream_diffs", natalie=natalie)
            res = dream.run(mode="preview")

            self.assertTrue(res["executed"])
            self.assertEqual(res["mode"], "preview")
            self.assertFalse(res["live_memory_modified"])
            self.assertEqual(res["diff"]["status"], "pending")
            self.assertTrue(pathlib.Path(res["diff"]["patch_path"]).exists())
            self.assertIn("--- memory/notes.before.txt", res["patch_content"])
            # Live notes table must remain unchanged
            self.assertEqual(len(store.list_notes()), len(notes_before))
            store.close()

    def test_05_meter_fields_and_savings_percentages(self) -> None:
        """5. Meter outputs input_tokens, output_tokens, cached_tokens, cost_usd, pass_rate, and both savings %."""
        store = MemoryStore(":memory:")
        meter = Meter(store)
        rec = meter.record(
            task_id="t_001",
            agent="Builder",
            model="gemini-3.6-flash",
            input_tokens=600,
            output_tokens=300,
            cached_tokens=350,
            cost_usd=0.0,
            pass_rate=93.5,
            mode="swarm",
            memory_driven=True,
            baseline_input_tokens=4000,
            baseline_total_tokens=1800,
        )
        summary = meter.summary()

        for field in ("input_tokens", "output_tokens", "cached_tokens", "cost_usd", "pass_rate"):
            self.assertIn(field, rec)
            self.assertIn(field, summary)

        self.assertAlmostEqual(summary["memory_turn_input_savings_pct"], 85.0, delta=0.5)
        self.assertAlmostEqual(summary["overall_task_savings_pct"], 50.0, delta=0.5)
        self.assertFalse(summary["accuracy_regression"])

        # Regression trigger check (<90% pass rate)
        meter.record(
            task_id="t_002",
            agent="Builder",
            model="gemini-3.6-flash",
            input_tokens=600,
            output_tokens=300,
            cached_tokens=300,
            cost_usd=0.0,
            pass_rate=70.0,
            mode="swarm",
        )
        reg = meter.summary()
        self.assertTrue(reg["accuracy_regression"])
        self.assertEqual(reg["recommended_strategy"], "conservative")
        store.close()

    def test_06_warden_blocks_above_hard_cap(self) -> None:
        """6. Warden blocks any billed call exceeding the configured hard cap."""
        with tempfile.TemporaryDirectory() as tmp:
            caps = probe_api_tier(api_key="AIzaPaid_demo", billing_deposited_usd=10.0)
            natalie = NatalieOps(pathlib.Path(tmp) / "ops", hard_cap_usd=0.20)
            warden = Warden(caps, natalie, hard_cap_usd=0.20, approval_threshold_usd=0.05)

            # Veo clip ($0.35) exceeds $0.20 hard cap -> DENY
            denied = warden.check(agent="Vision", tool="generate_video", units=1)
            self.assertEqual(denied.verdict, "DENY")
            self.assertIn("Hard cap exceeded", denied.reason)

            # Smaller billed call ($0.10) within $0.20 cap but above $0.05 threshold -> NEED_APPROVAL
            need = warden.check(agent="Vision", tool="paid_llm_call", custom_cost_usd=0.10)
            self.assertEqual(need.verdict, "NEED_APPROVAL")
            self.assertIsNotNone(need.approval_id)
            self.assertEqual(len(natalie.approval_queue), 1)

    def test_07_free_tier_disables_veo_keeps_image_speech(self) -> None:
        """7. Free-tier API key disables Veo with clear warning; image and speech remain allowed."""
        with tempfile.TemporaryDirectory() as tmp:
            # Pro plan alone with $0 deposited must stay on free tier
            caps = probe_api_tier(api_key="AIzaFree_key", billing_deposited_usd=0.0, has_ai_pro_plan=True)
            self.assertEqual(caps.tier, "free")
            self.assertFalse(caps.video_enabled)
            self.assertTrue(caps.image_enabled)
            self.assertTrue(caps.speech_enabled)
            self.assertIn("paid", (caps.warning or "").lower())

            natalie = NatalieOps(pathlib.Path(tmp) / "ops", hard_cap_usd=0.0)
            warden = Warden(caps, natalie, hard_cap_usd=0.0)

            veo_res = warden.check(agent="Vision", tool="generate_video")
            img_res = warden.check(agent="Vision", tool="generate_image")
            tts_res = warden.check(agent="Griot", tool="generate_speech")

            self.assertEqual(veo_res.verdict, "DENY")
            self.assertIn("Veo", veo_res.reason)
            self.assertEqual(img_res.verdict, "ALLOW")
            self.assertEqual(tts_res.verdict, "ALLOW")

    def test_08_no_external_supergravity_dependency(self) -> None:
        """8. Zero dependency on any external supergravity PyPI or npm package."""
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        self.assertFalse(manifest["external_supergravity_dependency"])

        for py_file in ROOT.rglob("*.py"):
            if py_file.name == "test_acceptance.py":
                continue
            text = py_file.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"^\s*(import|from)\s+supergravity\b", f"Forbidden import in {py_file}")

    def test_09_all_six_adapters_generated_and_valid(self) -> None:
        """9. Adapters for Antigravity, Claude Code, Cursor, Gemini CLI, Codex CLI, and Generic MCP are valid."""
        expected_targets = {
            "antigravity",
            "claude-code",
            "cursor",
            "gemini-cli",
            "codex-cli",
            "generic-mcp",
        }
        self.assertEqual(set(self.generated.keys()), expected_targets)

        # Validate every generated JSON file parses cleanly
        for json_path in (ROOT / "adapters").rglob("*.json"):
            parsed = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertIsInstance(parsed, dict)

        # Validate Codex TOML contains MCP server section
        codex_toml = (ROOT / "adapters/codex-cli/config.toml").read_text(encoding="utf-8")
        self.assertIn("[mcp_servers.aetherloom]", codex_toml)

        # Validate Skill Learning protects core skills and passes benchmark gate (>=5 tasks)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = pathlib.Path(tmp)
            (tmp_root / "benchmarks").mkdir()
            (tmp_root / "benchmarks/tasks.json").write_text(
                (ROOT / "benchmarks/tasks.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            store = MemoryStore(tmp_root / "s.db")
            pipeline = SkillLearningPipeline(tmp_root, store)
            with self.assertRaises(PermissionError):
                pipeline.draft_candidate("supergravity", "Attempt overwrite", "forbidden")
            pipeline.draft_candidate(
                "strict-worktree-checklist",
                "Procedural verification checklist",
                "Always isolate in git worktree, review diff, run test for verbatim output evidence, "
                "query fts5 bm25 slice within budget, check warden cap approval, enforce free-tier veo warning, "
                "and write dream preview patch pending.",
            )
            promo = pipeline.evaluate_and_promote("strict-worktree-checklist")
            self.assertTrue(promo["promoted"])
            self.assertTrue((tmp_root / "skills/learned/strict-worktree-checklist/SKILL.md").exists())
            store.close()

    def test_10_no_sentience_or_consciousness_claims(self) -> None:
        """10. Documentation never claims sentience, consciousness, or emotions."""
        for doc in list(ROOT.rglob("*.md")) + [ROOT / "manifest.json"]:
            text = doc.read_text(encoding="utf-8").lower()
            for pat in SENTIENCE_PATTERNS:
                self.assertNotRegex(text, pat, f"Forbidden sentience claim matched in {doc}")


def run_as_json() -> dict:
    TestAetherLoomAcceptance.setUpClass()
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestAetherLoomAcceptance)
    results = []
    passed = 0
    for test_case in suite:
        res = unittest.TestResult()
        test_case.run(res)
        ok = res.wasSuccessful()
        if ok:
            passed += 1
        err_msg = ""
        if res.failures:
            err_msg = res.failures[0][1]
        elif res.errors:
            err_msg = res.errors[0][1]
        results.append(
            {
                "id": test_case._testMethodName,
                "title": (test_case.shortDescription() or test_case._testMethodName).strip(),
                "passed": ok,
                "error": err_msg.strip() if err_msg else None,
            }
        )
    return {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "all_passed": passed == len(results),
        "tests": results,
    }


if __name__ == "__main__":
    if "--json" in sys.argv:
        report = run_as_json()
        print(json.dumps(report, indent=2))
        sys.exit(0 if report["all_passed"] else 1)
    unittest.main(verbosity=2)
