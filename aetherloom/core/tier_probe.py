"""Free-tier API key probe and media capability detection.

Critical billing realities enforced in code:
- Default free tier runs Gemini 3.6 Flash (~15 RPM / ~1,500 RPD).
- Google AI Pro $10/month API credits only activate if the API key's billing
  account holds at least $5 deposited. Never assume Pro alone unlocks paid APIs.
- Free-tier keys support generate_image (Nano Banana) and generate_speech (TTS)
  within free-tier rate limits.
- Veo video generation (generate_video) returns BAD_REQUEST on free-tier keys;
  it is disabled proactively with a clear message rather than failing at runtime.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from typing import Any, Callable, Dict, Optional


FREE_TIER_VEO_WARNING = (
    "Veo video generation (generate_video) is disabled on free-tier API keys "
    "because Veo has no free tier and returns BAD_REQUEST without a funded paid key. "
    "Note: Google AI Pro $10/month credits require at least $5 deposited in the billing account. "
    "Image generation (Nano Banana) and speech synthesis (TTS) remain enabled within free-tier rate limits."
)


@dataclass
class TierCapabilities:
    tier: str  # "free" or "paid"
    default_model: str
    rpm_limit: int
    rpd_limit: int
    image_enabled: bool
    speech_enabled: bool
    video_enabled: bool
    warning: Optional[str]
    pro_credit_note: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def probe_api_tier(
    api_key: Optional[str] = None,
    billing_deposited_usd: float = 0.0,
    has_ai_pro_plan: bool = True,
    probe_fn: Optional[Callable[[str], str]] = None,
) -> TierCapabilities:
    """Probe the configured API key and return concrete capability flags.

    Args:
        api_key: Explicit API key or reads GEMINI_API_KEY env var.
        billing_deposited_usd: Explicit deposited funds in the API billing account.
        has_ai_pro_plan: Whether user has Google AI Pro (does NOT unlock paid APIs without >=$5 deposited).
        probe_fn: Optional callable returning 'free' or 'paid' (or raising BAD_REQUEST).
    """
    key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "")
    pro_note = (
        "Google AI Pro includes $10/month Gemini API credits only when the billing account "
        "has at least $5 of its own deposited funds."
    )

    detected_tier = "free"

    if probe_fn is not None and key:
        try:
            res = probe_fn(key)
            if res == "paid":
                detected_tier = "paid"
        except Exception as exc:
            if "BAD_REQUEST" in str(exc).upper() or "BILLING" in str(exc).upper():
                detected_tier = "free"
    else:
        # Deterministic offline detection rules:
        # 1. Explicit paid marker or >=$5 deposited billing account unlocks paid tier.
        # 2. Google AI Pro alone with $0 deposited remains free tier.
        env_tier = os.environ.get("AETHERLOOM_API_TIER", "").strip().lower()
        if env_tier == "paid" and billing_deposited_usd >= 5.0:
            detected_tier = "paid"
        elif key.startswith("AIzaPaid_") or billing_deposited_usd >= 5.0:
            detected_tier = "paid"
        else:
            detected_tier = "free"

    if detected_tier == "paid":
        return TierCapabilities(
            tier="paid",
            default_model="gemini-3.6-flash",
            rpm_limit=1000,
            rpd_limit=50000,
            image_enabled=True,
            speech_enabled=True,
            video_enabled=True,
            warning=None,
            pro_credit_note=pro_note,
        )

    return TierCapabilities(
        tier="free",
        default_model="gemini-3.6-flash",
        rpm_limit=15,
        rpd_limit=1500,
        image_enabled=True,
        speech_enabled=True,
        video_enabled=False,
        warning=FREE_TIER_VEO_WARNING,
        pro_credit_note=pro_note,
    )
