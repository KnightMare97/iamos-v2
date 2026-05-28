"""IAMOS Shared Types
All core enums and type definitions used across domains.
Import from here — never redefine in individual domains.
"""
from enum import Enum

class ApprovalMode(int, Enum):
    OPERATOR_ONLY = 1
    OPERATOR_AND_CLIENT = 2
    AUTO = 3

class ContentItemState(str, Enum):
    PENDING = "PENDING"
    GENERATION_QUEUED = "GENERATION_QUEUED"
    DRAFT_READY = "DRAFT_READY"
    AWAITING_OPERATOR = "AWAITING_OPERATOR"
    AWAITING_CLIENT = "AWAITING_CLIENT"
    REVISION_REQUESTED = "REVISION_REQUESTED"
    APPROVED = "APPROVED"
    SCHEDULED = "SCHEDULED"
    PUBLISHING = "PUBLISHING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"
    DEAD = "DEAD"
    ESCALATED = "ESCALATED"

class CampaignState(str, Enum):
    PENDING = "PENDING"
    DRAFT_READY = "DRAFT_READY"
    AWAITING_OPERATOR = "AWAITING_OPERATOR"
    AWAITING_CLIENT = "AWAITING_CLIENT"
    REVISION_REQUESTED = "REVISION_REQUESTED"
    ACTIVE = "ACTIVE"

class PublishJobState(str, Enum):
    QUEUED = "QUEUED"
    ATTEMPTING = "ATTEMPTING"
    DONE = "DONE"
    FAILED = "FAILED"
    DEAD = "DEAD"

class AssetType(str, Enum):
    PHOTO = "photo"
    VIDEO = "video"
    AI_GENERATED = "ai_generated"

class AssetSource(str, Enum):
    CLIENT_UPLOAD = "client_upload"
    AI = "ai"
    SHOOTING = "shooting"

class AgentType(str, Enum):
    STRATEGY = "strategy"
    CONTENT = "content"
    REVISION = "revision"

class AggregateType(str, Enum):
    CONTENT_ITEM = "ContentItem"
    CAMPAIGN = "Campaign"
    PUBLISH_JOB = "PublishJob"
    CLIENT = "Client"

class TriggeredBy:
    """Helper to construct triggered_by strings."""
    @staticmethod
    def human(user_id: str) -> str:
        return f"human:{user_id}"

    @staticmethod    def agent(agent_type: AgentType) -> str:
        return f"agent:{agent_type.value}"
