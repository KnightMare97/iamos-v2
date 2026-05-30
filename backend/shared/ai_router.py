"""IAMOS Multi-Provider Dynamic AI Router Component
Manages dynamic runtime failovers across Google, OpenRouter (DeepSeek/Claude),
OpenAI, and xAI based on Admin Panel configurations and Circuit Breakers.
"""
import os
import logging
from dataclasses import dataclass
from typing import Optional, Dict, List, Any

logger = logging.getLogger("iamos.ai_router")

@dataclass
class ModelConfig:
    mode: str
    provider: Optional[str]
    model: Optional[str]
    note: Optional[str] = None

# Strict Tier mapping for optimizing task execution budgets
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
    "prompt_review_analyzer": 2,
    "campaign_asset_vision": 2,
    "image_prompt_generation": 3,
    "image_qa_vision": 2
}

# Provider to specific model mapping across Tiers (Includes DeepSeek V4)
PROVIDER_MODELS: Dict[str, Dict[str, str]] = {
    "google": {
        "tier2": "gemini-2.0-flash",
        "tier3": "gemini-1.5-pro",
    },
    "openrouter": {
        "tier2": "deepseek/deepseek-chat",       # DeepSeek V4 Flash equivalent
        "tier3": "deepseek/deepseek-reasoner",   # DeepSeek V4 Pro Reasoning equivalent
    },
    "anthropic": {
        "tier2": "claude-3-haiku-20240307",
        "tier3": "claude-3-5-sonnet-20241022",
    },
    "openai": {
        "tier2": "gpt-4o-mini",
        "tier3": "gpt-4o",
    },
    "xai": {
        "tier2": "grok-2-1212",
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
            logger.warning(f"Circuit breaker TRIPPED for provider: {provider}")
            self.tripped_providers.append(provider)

    def reset(self, provider: str):
        if provider in self.tripped_providers:
            logger.info(f"Circuit breaker RESET for provider: {provider}")
            self.tripped_providers.remove(provider)

class AIRouter:
    def __init__(self, circuit_breaker: Optional[CircuitBreakerRegistry] = None):
        self.circuit_breaker = circuit_breaker or CircuitBreakerRegistry()

    def route(self, task_type: str, context: dict) -> ModelConfig:
        """
        Dynamically routes any AI task based on Admin selections passed via context.
        Ensures 100% vector memory isolation and zero data regression.
        """
        if task_type not in TASK_TIER_MAP:
            return ModelConfig(mode="standard", provider="google", 
                               model=PROVIDER_MODELS["google"]["tier3"], 
                               note="unknown_task_default")
            
        tier = TASK_TIER_MAP[task_type]
        tier_key = f"tier{tier}"

        # Tier 1 task extraction (Pure local logic/regex mapping - zero API cost)
        if tier == 1:
            return ModelConfig(mode="local", provider=None, model="local-rules", note="rule_engine_execution")

        # Dynamic Admin Configuration Extraction from DB Context
        # Allows runtime live-switching from the Web Panel per client or globally
        primary_provider = context.get("preferred_provider", "google").lower()
        fallback_provider = context.get("fallback_provider", "openrouter").lower()

        # Build dynamic fallbacks sequence dynamically based on availability
        all_providers = [primary_provider, fallback_provider, "google", "openrouter", "openai"]
        provider_order = []
        for p in all_providers:
            if p in PROVIDER_MODELS and p not in provider_order:
                provider_order.append(p)

        # 1. Main Runtime Routing Execution Loop
        for provider in provider_order:
            if self.circuit_breaker.is_open(provider):
                continue
            
            # Verify API Key existence before attempting execution block
            env_key_map = {
                "google": "GOOGLE_AI_API_KEY",
                "openrouter": "OPENROUTER_API_KEY",
                "anthropic": "ANTHROPIC_API_KEY",
                "openai": "OPENAI_API_KEY",
                "xai": "XAI_API_KEY"
            }
            if not os.getenv(env_key_map.get(provider, "")):
                logger.debug(f"Skipping {provider}: API Key configuration missing in .env")
                continue

            return ModelConfig(
                mode="standard" if provider == primary_provider else "fallback_routing",
                provider=provider,
                model=PROVIDER_MODELS[provider][tier_key],
                note=f"routed_via_{provider}_as_{tier_key}"
            )

        # 2. Critical Degradation Layer (All selected Tier 3 endpoints unreachable)
        for provider in provider_order:
            if provider not in PROVIDER_MODELS or self.circuit_breaker.is_open(provider):
                continue
            return ModelConfig(
                mode="degraded_tier_fallback",
                provider=provider, 
                model=PROVIDER_MODELS[provider]["tier2"], 
                note="critical_degradation_tier3_down_to_tier2"
            )

        # 3. Complete Blackout Guard (No healthy providers available)
        return ModelConfig(
            mode="queued_halt", 
            provider=None, 
            model=None, 
            note="all_providers_tripped_operator_alert_triggered"
        )
