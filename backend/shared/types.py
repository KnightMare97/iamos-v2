from enum import Enum

class ClientStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    OFFBOARDED = "offboarded"

class ApprovalMode(int, Enum):
    OPERATOR_ONLY = 1          # 1 = Only operator reviews
    OPERATOR_AND_CLIENT = 2    # 2 = Operator first, then client approves
    AUTOMATIC = 3              # 3 = Auto-publish bypass

class PublishMode(int, Enum):
    MANUAL_TELEGRAM = 1        # Publish Mode 1: Delivery via Telegram Bot
    SEMI_AUTOMATED = 2
    FULLY_AUTOMATED = 3

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
    CANCELLED = "CANCELLED"    # Added for safe client offboarding chains

class CampaignState(str, Enum):
    PENDING = "PENDING"
    DRAFT_READY = "DRAFT_READY"
    AWAITING_OPERATOR = "AWAITING_OPERATOR"
    AWAITING_CLIENT = "AWAITING_CLIENT"
    REVISION_REQUESTED = "REVISION_REQUESTED"
    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"

class PublishJobState(str, Enum):
    QUEUED = "QUEUED"
    ATTEMPTING = "ATTEMPTING"
    DONE = "DONE"
    FAILED = "FAILED"
    DEAD = "DEAD"
    CANCELLED = "CANCELLED"
