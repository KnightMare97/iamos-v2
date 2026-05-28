from enum import Enum

class ClientStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    OFFBOARDED = "offboarded"

class ApprovalMode(int, Enum):
    MANUAL = 1
    SEMI_AUTO = 2
    FULLY_AUTO = 3

class PublishMode(int, Enum):
    MANUAL = 1
    SEMI_AUTO = 2
    FULLY_AUTO = 3
