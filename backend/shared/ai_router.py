"""IAMOS Multi-Provider AI Router Component
Manages dynamic failovers across Anthropic, OpenAI, Google, and xAI
based on Tier requirements, local circuit breakers, and client budgets.
"""
from dataclasses import dataclass
from typing import Optional, Dict, List, Any

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
    "observability_digest": 2,
    "reporting_narrative": 2,
    "prompt_review_analyzer": 2,    # Tier 2 Prompt Optimization Theme Analysis Task
    "campaign_asset_vision": 2,     # Vision Description for Ingested Campaign Assets
    "image_prompt_generation": 3,   # Tier 3 Prompt Expansion Strategy (Sonnet)
    "image_qa_vision": 2            # Tier 2 Multi-Factor Vision QA (Haiku/Mini)
}

PROVIDER_MODELS: Dict[str, Dict[str, str]] = {
    "anthropic": {
        "tier2": "claude-haiku-4-5",
        "tier3": "claude-sonnet-4-6",
    },
    "openai": {
        "tier2": "gpt-4o-mini",
        "tier3": "gpt-4o",
    },
    "google": {
        "tier2": "gemini-2.0-flash",
        "tier3": "gemini-2.5-pro",
    },
    "xai": {
        "tier2": "grok-3-mini",
        "tier3": "grok-3",
    }
}

class CircuitBreakerRegistry:
    def __init__(self):
        self.tripped_providers: List[str] = []

    def is_open(self, provider: str) -> bool:
        return provider in self.tripped_providers

    def trip(self, provider: str):
        if provider not in self.tripped_providers:
            self.tripped_providers.append(provider)

class AIRouter:
    def __init__(self, primary_provider: str = "anthropic", 
                 fallbacks: Optional[List[str]] = None,
                 circuit_breaker: Optional[CircuitBreakerRegistry] = None):
        self.primary_provider = primary_provider
        self.fallbacks = fallbacks or ["openai", "google", "xai"]
        self.circuit_breaker = circuit_breaker or CircuitBreakerRegistry()

    def monthly_budget_exhausted(self, client_id: Any) -> bool:
        return False

    def route(self, task_type: str, context: dict) -> ModelConfig:
        if task_type not in TASK_TIER_MAP:
            return ModelConfig(mode="standard", provider=self.primary_provider, 
                               model=PROVIDER_MODELS[self.primary_provider]["tier3"], 
                               note="unknown_task_default")
            
        tier = TASK_TIER_MAP[task_type]
        tier_key = f"tier{tier}"
        client_id = context.get("client_id")

        if tier == 1:
            return ModelConfig(mode="local", provider=None, model="local-rules", note="rule_engine_execution")

        if tier == 2 and self.monthly_budget_exhausted(client_id):
            return ModelConfig(mode="throttled", provider="google", model=PROVIDER_MODELS["google"]["tier2"], note="budget_throttled_to_flash")

        provider_order = [self.primary_provider] + self.fallbacks
        
        for provider in provider_order:
            if provider not in PROVIDER_MODELS:
                continue
            if self.circuit_breaker.is_open(provider):
                continue
            return ModelConfig(mode="standard", provider=provider, model=PROVIDER_MODELS[provider][tier_key])

        for provider in provider_order:
            if provider not in PROVIDER_MODELS or self.circuit_breaker.is_open(provider):
                continue
            return ModelConfig(mode="degraded_tier_fallback", provider=provider, 
                               model=PROVIDER_MODELS[provider]["tier2"], 
                               note="all_tier3_down_degraded_to_tier2")

        return ModelConfig(mode="queued_halt", provider=None, model=None, note="all_providers_tripped_operator_alerted")
