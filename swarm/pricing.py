"""Cost estimation for the paid APIs the swarm touches.

These numbers are the *list-price* rates we use to render real-time
spend in the Live View dashboard. They are intentionally conservative
and easy to tweak — replace with billed-actuals once we pipe each
provider's billing API in (Phase 5).

All values are USD.
"""

from __future__ import annotations

# Anthropic Claude — list price, per million tokens (Mar 2026 rate card).
ANTHROPIC_PRICING = {
    "claude-opus-4-7":     {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-6":   {"input":  3.00, "output": 15.00},
    "claude-haiku-4-5":    {"input":  0.80, "output":  4.00},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
}

# OpenAI — per million tokens.
OPENAI_PRICING = {
    "gpt-4.1":         {"input": 2.50, "output": 10.00},
    "gpt-4.1-mini":    {"input": 0.30, "output":  1.20},
    "gpt-4o":          {"input": 2.50, "output": 10.00},
    "gpt-4o-mini":     {"input": 0.15, "output":  0.60},
}

# ElevenLabs — per 1k characters synthesized, Creator plan list.
ELEVENLABS_PER_1K_CHARS = 0.18

# Shotstack stage tier — per output minute (rounded up).
SHOTSTACK_PER_OUTPUT_MINUTE = 0.05

# Generative-video providers — per second of generated B-roll.
SORA_PER_SECOND = 0.10
VEO_PER_SECOND = 0.35

# YouTube — free for upload; analytics counted under quota cost.
YOUTUBE_PER_UPLOAD = 0.0


def estimate_llm_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Look up per-token rates and return USD cost. Unknown models bill at 0."""
    table = _lookup_llm_pricing(model)
    if not table:
        return 0.0
    return (input_tokens * table["input"] + output_tokens * table["output"]) / 1_000_000


def estimate_elevenlabs_cost_usd(character_count: int) -> float:
    return (character_count / 1000.0) * ELEVENLABS_PER_1K_CHARS


def estimate_shotstack_cost_usd(duration_seconds: float) -> float:
    minutes = max(duration_seconds, 1) / 60.0
    return minutes * SHOTSTACK_PER_OUTPUT_MINUTE


def estimate_broll_cost_usd(provider: str, duration_seconds: float) -> float:
    rate = {"sora": SORA_PER_SECOND, "veo": VEO_PER_SECOND}.get((provider or "").lower(), 0.0)
    return rate * max(duration_seconds, 0)


def _lookup_llm_pricing(model: str) -> dict:
    m = (model or "").lower()
    for table in (ANTHROPIC_PRICING, OPENAI_PRICING):
        for k, v in table.items():
            if k.lower() == m:
                return v
    # Loose prefix match — "claude-opus-4-7-20260101" still hits opus pricing.
    for table in (ANTHROPIC_PRICING, OPENAI_PRICING):
        for k, v in table.items():
            if m.startswith(k.lower()):
                return v
    return {}
