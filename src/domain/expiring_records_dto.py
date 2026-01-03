from pydantic import BaseModel, ConfigDict

from domain.models import Record


class ExpiringRecordsDTO(BaseModel):
    model_config = ConfigDict(
        extra='ignore',
        arbitrary_types_allowed=True
    )

    record: Record
    days_before_expire: int

    def __gt__(self, other: 'ExpiringRecordsDTO') -> bool:
        return self.days_before_expire > other.days_before_expire

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ExpiringRecordsDTO):
            return False
        return other.record.id == self.record.id
