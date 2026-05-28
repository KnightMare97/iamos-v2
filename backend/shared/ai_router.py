"""IAMOS AI Router Component
Manages Tier routing, self-assessed confidence evaluation gates, 
budget throttling, and provider circuit breakers.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class ModelConfig:
    mode: str
    provider: Optional[str]
    model: Optional[str]
    note: Optional[str] = None

TASK_TIER_MAP: Dict[str, int] = {
    "strategy_rerank": 2,
    "strategy_generation": 3,
    "caption_draft": 2,
    "caption_escalated": 3,
    "feedback_classification": 1,
    "revision_standard": 2,
    "revision_complex": 3,
    "approval_summarization": 2,
    "moderation_rules": 1,
    "moderation_ambiguous": 2,
    "observability_digest": 2
}

TIER_MODEL_MAP: Dict[int, str] = {
    1: "local-nano-or-rules",
    2: "claude-3-haiku-20240307",
    3: "claude-3-5-sonnet-20240620"
}

class FakeCircuitBreaker:
    """Stub for system circuit breaker evaluating health of specific providers."""
    def is_open(self, target: str) -> bool:
        # Returns True if service is down/tripped
        return False

class AIRouter:
    def __init__(self, circuit_breaker: Optional[FakeCircuitBreaker] = None):
        self.circuit_breaker = circuit_breaker or FakeCircuitBreaker()

    def monthly_budget_exhausted(self, client_id: Any) -> bool:
        """Stub checking if a client has blown past their computational quota."""
        return False

    def route(self, task_type: str, context: dict) -> ModelConfig:
        if task_type not in TASK_TIER_MAP:
            # Safe default fallback
            return ModelConfig(mode="standard", provider="anthropic", model=TIER_MODEL_MAP[3], note="unknown_task_default")
            
        tier = TASK_TIER_MAP[task_type]
        client_id = context.get("client_id")

        # 1. Evaluate Tier 3 Outage Fallbacks
        if tier == 3 and self.circuit_breaker.is_open("anthropic_sonnet"):
            if self.circuit_breaker.is_open("anthropic_haiku"):
                return ModelConfig(mode="degraded", provider=None, model=None, note="all_providers_down")
            return ModelConfig(mode="degraded_fallback", provider="anthropic", model="claude-3-haiku-20240307", note="sonnet_outage_fallback_to_haiku")

        # 2. Check Client Budgets for Contextual Tasks
        if tier == 2 and self.monthly_budget_exhausted(client_id):
            return ModelConfig(mode="throttled", provider="anthropic", model="claude-3-haiku-20240307", note="budget_throttled")

        # 3. Handle Tier 1 Local Rule Engine Tasks
        if tier == 1:
            return ModelConfig(mode="local", provider=None, model=TIER_MODEL_MAP[1], note="rule_engine_or_local_nano")

        # 4. Standard Flow Execution
        return ModelConfig(mode="standard", provider="anthropic", model=TIER_MODEL_MAP[tier])
