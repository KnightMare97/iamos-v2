"""IAMOS State Machine Definitions
Single source of truth for all valid state transitions.
The orchestrator uses this to validate and execute transitions.
"""
from typing import Optional
from backend.shared.types import (
    ContentItemState,
    CampaignState,
    PublishJobState,
    ApprovalMode,
)

# Each transition: (from_state, event_type) -> (to_state, guard_description)
# Guard conditions are enforced by the orchestrator before applying transition.
CONTENT_ITEM_TRANSITIONS: dict[tuple, dict] = {
    (ContentItemState.PENDING, "calendar.approved"): {
        "to": ContentItemState.GENERATION_QUEUED,
        "guard": None,
    },
    (ContentItemState.GENERATION_QUEUED, "agent.content.completed"): {
        "to": ContentItemState.DRAFT_READY,
        "guard": None,
    },
    (ContentItemState.DRAFT_READY, "approval.requested"): {
        "to": ContentItemState.AWAITING_OPERATOR,
        "guard": None,
    },
    (ContentItemState.AWAITING_OPERATOR, "operator.approved"): {
        "to": ContentItemState.AWAITING_CLIENT,
        "guard": "approval_mode == OPERATOR_AND_CLIENT",
    },
    (ContentItemState.AWAITING_OPERATOR, "operator.approved.auto_client"): {
        "to": ContentItemState.APPROVED,
        "guard": "approval_mode == OPERATOR_ONLY",
    },
    (ContentItemState.AWAITING_OPERATOR, "operator.rejected"): {
        "to": ContentItemState.REVISION_REQUESTED,
        "guard": None,
    },
    (ContentItemState.AWAITING_OPERATOR, "approval.timeout"): {
        "to": ContentItemState.ESCALATED,
        "guard": None,
    },
    (ContentItemState.AWAITING_CLIENT, "client.approved"): {
        "to": ContentItemState.APPROVED,
        "guard": None,
    },
    (ContentItemState.AWAITING_CLIENT, "client.rejected"): {
        "to": ContentItemState.REVISION_REQUESTED,
        "guard": None,
    },
    (ContentItemState.AWAITING_CLIENT, "approval.timeout"): {
        "to": ContentItemState.ESCALATED,
        "guard": None,
    },
    (ContentItemState.REVISION_REQUESTED, "agent.revision.completed"): {
        "to": ContentItemState.DRAFT_READY,
        "guard": "revision_count < max_revisions",
    },
    (ContentItemState.REVISION_REQUESTED, "agent.revision.completed.max"): {
        "to": ContentItemState.ESCALATED,
        "guard": "revision_count >= max_revisions",
    },
    (ContentItemState.APPROVED, "publish.scheduled"): {
        "to": ContentItemState.SCHEDULED,
        "guard": None,
    },
    (ContentItemState.SCHEDULED, "publish.attempting"): {
        "to": ContentItemState.PUBLISHING,
        "guard": None,
    },
    (ContentItemState.PUBLISHING, "publish.succeeded"): {
        "to": ContentItemState.PUBLISHED,
        "guard": None,
    },
    (ContentItemState.PUBLISHING, "publish.failed"): {
        "to": ContentItemState.FAILED,
        "guard": None,
    },
    (ContentItemState.FAILED, "publish.retrying"): {
        "to": ContentItemState.PUBLISHING,
        "guard": "attempts < max_attempts",
    },
    (ContentItemState.FAILED, "publish.dead"): {
        "to": ContentItemState.DEAD,
        "guard": "attempts >= max_attempts",
    },
    (ContentItemState.DEAD, "manual.retry"): {
        "to": ContentItemState.PUBLISHING,
        "guard": "human triggered",
    },
}

CAMPAIGN_TRANSITIONS: dict[tuple, dict] = {
    (CampaignState.PENDING, "agent.strategy.completed"): {
        "to": CampaignState.DRAFT_READY,
        "guard": None,
    },
    (CampaignState.DRAFT_READY, "approval.requested"): {
        "to": CampaignState.AWAITING_OPERATOR,
        "guard": None,
    },
    (CampaignState.AWAITING_OPERATOR, "operator.approved"): {
        "to": CampaignState.AWAITING_CLIENT,
        "guard": "client_calendar_approval == True",
    },
    (CampaignState.AWAITING_OPERATOR, "operator.approved.no_client"): {
        "to": CampaignState.ACTIVE,
        "guard": "client_calendar_approval == False",
    },
    (CampaignState.AWAITING_OPERATOR, "operator.rejected"): {
        "to": CampaignState.REVISION_REQUESTED,
        "guard": None,
    },
    (CampaignState.AWAITING_CLIENT, "client.approved"): {
        "to": CampaignState.ACTIVE,
        "guard": None,
    },
    (CampaignState.AWAITING_CLIENT, "client.rejected"): {
        "to": CampaignState.REVISION_REQUESTED,
        "guard": None,
    },
    (CampaignState.REVISION_REQUESTED, "agent.strategy.completed"): {
        "to": CampaignState.DRAFT_READY,
        "guard": None,
    },
    (CampaignState.ACTIVE, "period.ended"): {
        "to": CampaignState.PENDING,
        "guard": None,
    },
}

PUBLISH_JOB_TRANSITIONS: dict[tuple, dict] = {
    (PublishJobState.QUEUED, "publish.attempting"): {
        "to": PublishJobState.ATTEMPTING,
        "guard": None,
    },
    (PublishJobState.ATTEMPTING, "publish.succeeded"): {
        "to": PublishJobState.DONE,
        "guard": None,
    },
    (PublishJobState.ATTEMPTING, "publish.failed"): {
        "to": PublishJobState.FAILED,
        "guard": None,
    },
    (PublishJobState.FAILED, "publish.retrying"): {
        "to": PublishJobState.ATTEMPTING,
        "guard": "attempts < max_attempts",
    },
    (PublishJobState.FAILED, "publish.dead"): {
        "to": PublishJobState.DEAD,
        "guard": "attempts >= max_attempts",
    },
    (PublishJobState.DEAD, "manual.retry"): {
        "to": PublishJobState.ATTEMPTING,
        "guard": "human triggered",
    },
}

def get_next_state(
    state_machine: dict,
    current_state,
    event_type: str,
) -> Optional[dict]:
    """
    Returns the transition dict if valid, None if not.
    Orchestrator is responsible for checking guard conditions.
    """
    return state_machine.get((current_state, event_type))
