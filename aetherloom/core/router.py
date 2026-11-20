"""Router — Mode classification (swarm, teamwork, hybrid) and accuracy-preserving model routing.

Strategy rules:
- Retrieve only relevant slices and memory hits; cache stable prompt prefixes.
- Route bounded implementation/retrieval to gemini-3.6-flash (free-tier default).
- NEVER compress relevant context to meet a token number.
- If Meter reports accuracy_regression (pass_rate < 90%), revert immediately to 'conservative'.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List


SWARM_KEYWORDS = (
    "refactor",
    "rename",
    "migrate",
    "multi-file",
    "multifile",
    "multi-module",
    "parallel",
    "batch",
    "across files",
    "across modules",
    "update imports",
    "lint",
    "bulk",
)

TEAMWORK_KEYWORDS = (
    "research",
    "multi-day",
    "multiday",
    "milestone",
    "rfc",
    "architecture",
    "deep dive",
    "audit",
    "verify",
    "verification",
    "benchmark",
    "specification",
    "investigate",
    "long-running",
    "report",
)

HEAVY_REASONING_AGENTS = {
    "commander",
    "critic",
    "adversary",
    "challenger",
    "auditor",
    "success_auditor",
    "docminer",
}


@dataclass
class RouteDecision:
    mode: str  # "swarm", "teamwork", "hybrid"
    strategy: str  # "standard", "conservative"
    swarm_signals: List[str]
    teamwork_signals: List[str]
    active_agents: List[str]
    model_assignments: Dict[str, str]
    context_budget_tokens: int
    prompt_prefix_caching: bool
    compress_relevant_context: bool
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class Router:
    """Deterministic mode classifier and accuracy-preserving token router."""

    def __init__(
        self,
        fast_model: str = "gemini-3.6-flash",
        reasoning_model: str = "gemini-3.6-flash-thinking",
    ) -> None:
        self.fast_model = fast_model
        self.reasoning_model = reasoning_model

    def classify(
        self,
        goal: str,
        accuracy_regression: bool = False,
    ) -> RouteDecision:
        text = (goal or "").lower()
        swarm_hits = [kw for kw in SWARM_KEYWORDS if re.search(rf"\b{re.escape(kw)}\b", text)]
        teamwork_hits = [kw for kw in TEAMWORK_KEYWORDS if re.search(rf"\b{re.escape(kw)}\b", text)]

        if swarm_hits and teamwork_hits:
            mode = "hybrid"
            active_agents = [
                "commander",
                "router",
                "archivist",
                "codemapper",
                "scout",
                "builder",
                "refactorer",
                "tester",
                "adversary",
                "critic",
                "challenger",
                "auditor",
                "success_auditor",
                "warden",
            ]
            rationale = (
                f"Detected both parallel implementation signals ({', '.join(swarm_hits)}) "
                f"and multi-milestone/research signals ({', '.join(teamwork_hits)}). "
                "Running parallel worktree sprints bounded by milestone verification gates."
            )
        elif teamwork_hits:
            mode = "teamwork"
            active_agents = [
                "commander",
                "router",
                "archivist",
                "scout",
                "docminer",
                "codemapper",
                "builder",
                "tester",
                "critic",
                "challenger",
                "auditor",
                "success_auditor",
                "warden",
            ]
            rationale = (
                f"Detected deep research/milestone signals ({', '.join(teamwork_hits)}). "
                "Executing layered milestones gated by Critic + Challenger + Auditor and final SuccessAuditor."
            )
        else:
            mode = "swarm"
            active_agents = [
                "commander",
                "router",
                "archivist",
                "codemapper",
                "builder",
                "refactorer",
                "tester",
                "adversary",
                "warden",
            ]
            rationale = (
                f"Detected parallelizable implementation signals ({', '.join(swarm_hits) or 'scoped code edit'}). "
                "Dispatching isolated git worktree Builders with live review-only Adversary; idle agents hold zero tokens."
            )

        strategy = "conservative" if accuracy_regression else "standard"
        context_budget = 2400 if strategy == "conservative" else 1200

        model_assignments: Dict[str, str] = {}
        for agent in active_agents:
            if strategy == "conservative" or agent in HEAVY_REASONING_AGENTS:
                model_assignments[agent] = self.reasoning_model
            else:
                model_assignments[agent] = self.fast_model

        return RouteDecision(
            mode=mode,
            strategy=strategy,
            swarm_signals=swarm_hits,
            teamwork_signals=teamwork_hits,
            active_agents=active_agents,
            model_assignments=model_assignments,
            context_budget_tokens=context_budget,
            prompt_prefix_caching=True,
            compress_relevant_context=False,  # Hard invariant: never compress relevant text
            rationale=rationale,
        )
