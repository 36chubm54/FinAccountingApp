from enum import StrEnum


class ImportPolicy(StrEnum):
    FULL_BACKUP = "full_backup"
    CURRENT_RATE = "current_rate"
    LEGACY = "legacy"
