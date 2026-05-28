# IAMOS Chain Model AI Architecture Redesign Spec

## Core Objectives
1. Eliminate single-provider premium tier model dependency.
2. Optimize token budgets and reduce cost by 64% using adaptive routing.
3. Establish robust confidence evaluation gates and fail-safes (Graceful Degradation).

## Per-Domain Specifications

### 1. Strategy Generation Chain
- **Step 1 (Tier 1 - Local DB):** Retrieve top-20 memory records via pgvector (Pure DB operation).
- **Step 2 (Tier 2 - Haiku):** Re-rank 20 records. Output top-5 with scores. Budget: 600 in / 200 out.
- **Step 3 (Tier 3 - Sonnet):** Generate full calendar using top-5 records context. Budget: 1500 in / 2000 out.
- **Fail-safe:** If Step 3 times out/fails, fall back to Tier 2 generating a skeleton calendar using fixed client category templates. Operator is alerted.
- **Confidence Gate:** If all re-ranked records similarity < 0.4, skip memory context entirely (`memory_context_skipped = true`).

### 2. Caption Generation Chain
- **Step 1 (Tier 2 - Haiku):** Draft caption from theme and brand voice. Output JSON with `caption`, `confidence_score`, and `flags`. Budget: 400 in / 200 out.
- **Confidence Gate:** If `confidence_score` >= 0.8 AND `flags` is empty -> emit `content.draft.ready` directly (Handles ~70% of loads).
- **Step 2 (Tier 3 - Sonnet Escalation):** If score < 0.8 OR flags present -> Escalate to Sonnet. Log reason.

### 3. Caption Revision Chain
- **Step 1 (Tier 1 - Regex/Rules):** Parse feedback to classify revision type.
- **Step 2 (Tier 2 - Haiku):** Handle standard tone/length/structural fixes. Budget: 300 in / 150 out.
- **Step 3 (Tier 3 - Sonnet):** Handle complex re-writes flagged by step 1. Max 2 Tier 3 escalations before cascading to human operator loop.

### 4. Approval Summarization (New Module)
- **Tier 2 (Haiku):** Produces batch summary evaluations when operator has 20+ pending items to intercept conflicts or language anomalies.

### 5. Moderation & Observability
- **Moderation:** Rule-engine handles constraints. Tier 2 Haiku triggers only on ambiguous border flags.
- **Observability:** Nightly Tier 2 Agent digest analyzing the last 50 logging events for structural trends.

## Multi-Provider AI Failover Specification
- **Interface Driven:** The execution workers must utilize a `ModelProvider` abstract base interface. Real-world client managers for Anthropic, OpenAI, Google, and xAI must implement this interface natively.
- **Circuit Breaker Policy:** If a network timeout, 5xx API boundary state, or rate limit threshold triggers a block on the active provider, the `AIRouter` immediately trips that provider's circuit and falls back to the next healthy provider in sequence.
- **Failover Order:** Primary (`AI_PRIMARY_PROVIDER`) -> Fallback 1 -> Fallback 2 -> Fallback 3.

## Daily Story Counter Override Logic
- **Precedence Rules:** Content generation engines evaluating اسلات‌های زمانی calendar items MUST read `daily_story_overrides` first. If a match is absent, fall back to `clients.stories_per_day`.
- **Zero-Slot Exclusions:** A `stories_count = 0` override explicitly marks that date as a freeze/skip window. No story items will be appended to the pipeline for processing.
- **Strategy Injection:** The dynamic prompt generation worker for Strategy execution must fetch the full month mapping of overrides and pass it as a contextual variables map `{daily_overrides}` directly to the LLM context.
