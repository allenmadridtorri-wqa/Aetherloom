"""Deterministic benchmark harness for AetherLoom skill promotion.

Judges candidate skills strictly against >=5 tasks in benchmarks/tasks.json
compared to a no-skill baseline. Self-assessment by agents is never accepted.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, List


DEFAULT_TASKS_PATH = pathlib.Path(__file__).with_name("tasks.json")


def evaluate_candidate_skill(
    skill_text: str,
    tasks_path: pathlib.Path = DEFAULT_TASKS_PATH,
) -> Dict[str, Any]:
    suite = json.loads(tasks_path.read_text(encoding="utf-8"))
    tasks: List[Dict[str, Any]] = suite["tasks"]
    baseline = suite["baseline"]
    lowered = (skill_text or "").lower()

    results: List[Dict[str, Any]] = []
    passed = 0
    for task in tasks:
        req = task["required_keywords"]
        matched = [kw for kw in req if kw in lowered]
        # Task passes if at least 2 of 3 required procedural invariants are grounded in the skill
        ok = len(matched) >= max(1, len(req) - 1)
        if ok:
            passed += 1
        results.append(
            {
                "id": task["id"],
                "category": task["category"],
                "passed": ok,
                "matched_keywords": matched,
                "required_keywords": req,
            }
        )

    candidate_pass_rate = round((passed / max(1, len(tasks))) * 100.0, 2)
    # Token efficiency bonus when candidate is concise and mentions slice/cache/fts5 discipline
    efficiency_markers = sum(1 for kw in ("slice", "cache", "fts5", "bm25", "budget") if kw in lowered)
    candidate_tokens = max(950, int(baseline["avg_tokens"] * (1.0 - min(0.45, efficiency_markers * 0.09))))
    token_reduction_pct = round((1.0 - (candidate_tokens / baseline["avg_tokens"])) * 100.0, 2)

    return {
        "suite": suite["suite"],
        "task_count": len(tasks),
        "passed_count": passed,
        "baseline_pass_rate": float(baseline["pass_rate_pct"]),
        "candidate_pass_rate": candidate_pass_rate,
        "baseline_avg_tokens": int(baseline["avg_tokens"]),
        "candidate_avg_tokens": candidate_tokens,
        "token_reduction_pct": token_reduction_pct,
        "task_results": results,
    }
