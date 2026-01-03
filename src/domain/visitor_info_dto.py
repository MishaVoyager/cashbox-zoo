import re
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, field_validator, ConfigDict


class VisitorInfoDTO(BaseModel):
    model_config = ConfigDict(extra='ignore')

    visitor_id: int
    visitor_email: str
    visitor_name: str
    visitor_username: str
    resource_name: str
    resource_id: int
    record_id: int
    take_date: Optional[datetime] = None
    return_date: Optional[datetime] = None
    enqueue_date: Optional[datetime] = None
    finished: bool = False
    address: Optional[str] = None

    def values(self) -> List[str]:
        return [
            str(self.visitor_id),
            self.visitor_email,
            self.visitor_name,
            self.resource_name,
            str(self.resource_id),
            str(self.record_id),
            self.take_date.strftime(r'%d.%m.%Y') if self.take_date is not None else " ",
            self.return_date.strftime(r'%d.%m.%Y') if self.return_date is not None else " ",
            self.enqueue_date.strftime(r'%d.%m.%Y') if self.enqueue_date is not None else " ",
            str(self.finished),
            self.address if self.address is not None else " "
        ]

    @field_validator("visitor_email")
    def check_user_email(cls, user_email: Optional[str]) -> Optional[str]:
        if user_email is None:
            return None
        if not re.search(r"^.*@((skbkontur)|(kontur))\.\w+$", user_email):
            raise ValueError("Почта не соответствует формату контуровской")
        return user_email

    @field_validator("take_date", "return_date", mode="before")
    def check_return_date(cls, some_date: Optional[str | datetime]) -> Optional[datetime]:
        if some_date is None:
            return None
        elif isinstance(some_date, str):
            if not re.search(r"^\d{2}.\d{2}.\d{4}$", some_date):
                raise ValueError("Дата не соответствует формату дд.мм.гггг")
            day, month, year = map(int, some_date.split("."))
            date = datetime(year, month, day)
        elif isinstance(some_date, datetime):
            date = some_date
        else:
            raise ValueError("Тип даты должен быть str или datetime")
        return date

    def __gt__(self, other: 'VisitorInfoDTO') -> bool:
        return self.take_date > other.take_date

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VisitorInfoDTO):
            return False
        return other.visitor_id == self.visitor_id
