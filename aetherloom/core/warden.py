"""Warden — Spend and permission guardrail enforced in code.

Every billed call (Vision, Griot, media MCP) must call Warden.check(...) first.
Decision flow:
  cost preview -> free-tier capability check -> freeze check -> hard cap check -> approval check
Returns: ALLOW, DENY, or NEED_APPROVAL.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

from core.natalie import NatalieOps
from core.tier_probe import FREE_TIER_VEO_WARNING, TierCapabilities


# Deterministic unit pricing preview table (USD)
TOOL_UNIT_COSTS_USD: Dict[str, float] = {
    "generate_video": 0.35,   # Veo billed per clip (~5-8s) — no free tier
    "generate_image": 0.00,   # Nano Banana free within free-tier RPM/RPD; $0.03 on paid high-volume
    "generate_speech": 0.00,  # TTS free within free-tier RPM/RPD; $0.01 on paid high-volume
    "paid_llm_call": 0.05,
}


@dataclass
class WardenDecision:
    verdict: str  # "ALLOW", "DENY", "NEED_APPROVAL"
    agent: str
    tool: str
    estimated_cost_usd: float
    current_spend_usd: float
    hard_cap_usd: float
    reason: str
    approval_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class Warden:
    """Enforces spend caps, free-tier media gates, and N.A.T.A.L.I.E. approval queuing."""

    def __init__(
        self,
        capabilities: TierCapabilities,
        natalie: NatalieOps,
        hard_cap_usd: float = 0.0,
        approval_threshold_usd: float = 0.0,
    ) -> None:
        self.capabilities = capabilities
        self.natalie = natalie
        self.hard_cap_usd = float(hard_cap_usd)
        self.approval_threshold_usd = float(approval_threshold_usd)

    def preview_cost(self, tool: str, units: int = 1, custom_cost_usd: Optional[float] = None) -> float:
        if custom_cost_usd is not None:
            return round(max(0.0, float(custom_cost_usd)), 6)
        if tool == "generate_video":
            return round(TOOL_UNIT_COSTS_USD["generate_video"] * max(1, units), 6)
        if self.capabilities.tier == "free" and tool in ("generate_image", "generate_speech"):
            return 0.0
        if tool == "generate_image":
            return round(0.03 * max(1, units), 6)
        if tool == "generate_speech":
            return round(0.01 * max(1, units), 6)
        return round(TOOL_UNIT_COSTS_USD.get(tool, 0.02) * max(1, units), 6)

    def check(
        self,
        agent: str,
        tool: str,
        units: int = 1,
        custom_cost_usd: Optional[float] = None,
    ) -> WardenDecision:
        estimated = self.preview_cost(tool, units=units, custom_cost_usd=custom_cost_usd)
        current_spend = self.natalie.spent_usd
        effective_cap = self.hard_cap_usd

        # 1. Free-tier Veo block (prevents runtime BAD_REQUEST)
        if tool == "generate_video" and not self.capabilities.video_enabled:
            self.natalie.log_event(
                "warden_denied_free_tier_veo",
                {"agent": agent, "tool": tool, "estimated_cost_usd": estimated},
            )
            return WardenDecision(
                verdict="DENY",
                agent=agent,
                tool=tool,
                estimated_cost_usd=estimated,
                current_spend_usd=current_spend,
                hard_cap_usd=effective_cap,
                reason=FREE_TIER_VEO_WARNING,
            )

        # 2. Freeze check from N.A.T.A.L.I.E.
        if self.natalie.billed_agents_frozen and estimated > 0:
            self.natalie.log_event(
                "warden_denied_frozen",
                {"agent": agent, "tool": tool, "estimated_cost_usd": estimated},
            )
            return WardenDecision(
                verdict="DENY",
                agent=agent,
                tool=tool,
                estimated_cost_usd=estimated,
                current_spend_usd=current_spend,
                hard_cap_usd=effective_cap,
                reason="Billed agents are frozen by N.A.T.A.L.I.E. because spend is at or near the hard cap.",
            )

        # 3. Hard cap check (strict)
        if estimated > 0 and (current_spend + estimated) > effective_cap:
            self.natalie.log_event(
                "warden_denied_hard_cap",
                {
                    "agent": agent,
                    "tool": tool,
                    "estimated_cost_usd": estimated,
                    "current_spend_usd": current_spend,
                    "hard_cap_usd": effective_cap,
                },
            )
            return WardenDecision(
                verdict="DENY",
                agent=agent,
                tool=tool,
                estimated_cost_usd=estimated,
                current_spend_usd=current_spend,
                hard_cap_usd=effective_cap,
                reason=(
                    f"Hard cap exceeded: projected spend ${current_spend + estimated:.2f} "
                    f"exceeds configured hard cap ${effective_cap:.2f}."
                ),
            )

        # 4. Approval threshold check (Veo always requires approval on paid keys too)
        if estimated > 0 and (estimated > self.approval_threshold_usd or tool == "generate_video"):
            req = self.natalie.enqueue_approval(
                agent=agent,
                tool=tool,
                estimated_cost_usd=estimated,
                reason=(
                    f"Warden cost preview ${estimated:.2f} for {tool} by {agent} "
                    f"requires explicit approval before execution."
                ),
            )
            return WardenDecision(
                verdict="NEED_APPROVAL",
                agent=agent,
                tool=tool,
                estimated_cost_usd=estimated,
                current_spend_usd=current_spend,
                hard_cap_usd=effective_cap,
                reason=req.reason,
                approval_id=req.id,
            )

        # 5. Free-tier allowed media or within pre-approved budget
        self.natalie.log_event(
            "warden_allowed",
            {
                "agent": agent,
                "tool": tool,
                "estimated_cost_usd": estimated,
                "tier": self.capabilities.tier,
            },
        )
        return WardenDecision(
            verdict="ALLOW",
            agent=agent,
            tool=tool,
            estimated_cost_usd=estimated,
            current_spend_usd=current_spend,
            hard_cap_usd=effective_cap,
            reason=(
                f"Allowed on {self.capabilities.tier} tier within rate limits "
                f"(estimated cost ${estimated:.2f})."
            ),
        )
