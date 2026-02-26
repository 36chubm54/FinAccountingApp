from infrastructure.repositories import RecordRepository


class RecordService:
    def __init__(self, repository: RecordRepository) -> None:
        self._repository = repository

    def update_amount_kzt(self, record_id: int, new_amount_kzt: float) -> None:
        record = self._repository.get_by_id(int(record_id))
        if record.transfer_id is not None:
            raise ValueError("Transfer-linked records cannot be edited")
        updated = record.with_updated_amount_kzt(float(new_amount_kzt))
        self._repository.replace(updated)
