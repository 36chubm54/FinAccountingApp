import logging
from typing import List, Tuple

from domain.records import Record

logger = logging.getLogger(__name__)


def import_records_from_csv(filepath: str) -> Tuple[List[Record], float]:
    try:
        from utils.csv_utils import import_records_from_csv as _import_records_from_csv

        return _import_records_from_csv(filepath)
    except Exception:
        logger.exception("Failed to import records from csv: %s", filepath)
        raise


def import_records_from_xlsx(filepath: str) -> Tuple[List[Record], float]:
    try:
        from utils.excel_utils import (
            import_records_from_xlsx as _import_records_from_xlsx,
        )

        return _import_records_from_xlsx(filepath)
    except Exception:
        logger.exception("Failed to import records from xlsx: %s", filepath)
        raise


def import_mandatory_expenses_from_csv(filepath: str) -> List:
    try:
        from utils.csv_utils import import_mandatory_expenses_from_csv

        return import_mandatory_expenses_from_csv(filepath)
    except Exception:
        logger.exception("Failed to import mandatory expenses from csv: %s", filepath)
        raise


def import_mandatory_expenses_from_xlsx(filepath: str) -> List:
    try:
        from utils.excel_utils import import_mandatory_expenses_from_xlsx

        return import_mandatory_expenses_from_xlsx(filepath)
    except Exception:
        logger.exception("Failed to import mandatory expenses from xlsx: %s", filepath)
        raise
