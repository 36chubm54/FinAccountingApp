from enum import Enum


class ImportPolicy(str, Enum):
    FULL_BACKUP = "full_backup"
    CURRENT_RATE = "current_rate"
    LEGACY = "legacy"
