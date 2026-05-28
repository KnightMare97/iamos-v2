# Reporting Domain Specification

## Architecture & Isolation
The Reporting domain is strictly decoupled from `observability`. 
- **Observability:** Append-only event store and active engine cost metrics.
- **Reporting:** Windowed aggregates, computed human-centric trends, and AI narratives serving the management dashboard.

## Aggregation Pipeline (Cron Execution)
- **Schedule:** Every Monday at 06:00 Asia/Tehran.
- **Mechanism:** Pure SQL calculations over the `events` and `agent_calls` tables for the `[week_start, week_end]` boundary.
- **Event Emission:** Triggers `report.generated` payload containing JSON report summaries once written to the DB.

## AI Narrative Summary Layer (Tier 2 Integration)
Immediately after raw SQL aggregation completes, a Tier 2 (Haiku) call is made via the `AIRouter` using `task_type="approval_summarization"` or similar.
- **Input Context:** Raw aggregate rows + historical metrics from the previous 2 weeks.
- **Output:** 3-4 plain-text sentences capturing the trajectory of the account (e.g., brand voice progress, cost savings, anomalies).

## Specifications for Derived Signals (Smart Fields)
1. **Revision Rate Trend (`revision_rate_trend_percentage`):** `((Current Week Revision Rate - Prior Week Revision Rate) / Prior Week Revision Rate) * 100`. A negative value validates prompt engineering and system calibration success.
2. **Operator Workload Score (`operator_workload_score`):** Derived from `avg_approval_hours`. If average hours in queue > 12 -> Flag as `overloaded`.
3. **Prompt Quality Metric (`tier3_escalation_rate`):** `tier3_calls / (tier2_calls + tier3_calls)`. If this holds > 40% across a standard content cycle, it registers an alert that the client-specific Tier 2 baseline prompts require a manual engineering refactor.
