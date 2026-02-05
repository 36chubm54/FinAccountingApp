import logging
from typing import List

logger = logging.getLogger(__name__)


def import_report_from_xlsx(filepath: str):
    try:
        from utils.excel_utils import report_from_xlsx

        return report_from_xlsx(filepath)
    except Exception:
        logger.exception("Failed to import report from xlsx: %s", filepath)
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
