import re
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, field_validator, ConfigDict


class ResourceInfoDTO(BaseModel):
    model_config = ConfigDict(extra='ignore')

    id: int
    name: str
    category_name: str
    vendor_code: str
    reg_date: Optional[datetime] = None
    firmware: Optional[str] = None
    comment: Optional[str] = None
    user_email: Optional[str] = None
    address: Optional[str] = None
    take_date: Optional[datetime] = None
    return_date: Optional[datetime] = None

    def short_str(self) -> str:
        return f"{self.name} с id {self.id} и артикулом {self.vendor_code}"

    def values(self) -> List[str]:
        return [
            str(self.id),
            self.name,
            self.category_name,
            self.vendor_code,
            self.reg_date.strftime(r'%d.%m.%Y') if self.reg_date is not None else " ",
            self.firmware if self.firmware is not None else " ",
            self.comment if self.comment is not None else " ",
            self.user_email if self.user_email is not None else " ",
            self.address if self.address is not None else " ",
            self.take_date.strftime(r'%d.%m.%Y') if self.take_date is not None else " ",
            self.return_date.strftime(r'%d.%m.%Y') if self.return_date is not None else " "
        ]

    def description(self) -> str:
        result = [
            f"{self.id}. {self.name} ({self.category_name})",
            f"Артикул: {self.vendor_code}"
        ]
        if self.reg_date:
            result.append(f"Зарегистрирован {self.reg_date.strftime(r'%d.%m.%Y')}")
        if self.firmware:
            result.append(f"Прошивка: {self.firmware}")
        if self.comment:
            result.append(f"Коммент: {self.comment}")
        if self.user_email:
            result.append(f"У пользователя {self.user_email}")
        if self.return_date:
            result.append(f"Освободится: {self.return_date.strftime(r'%d.%m.%Y')}")
        if self.address:
            result.append(f"Находится: {self.address}")
        return '\n'.join([i for i in result if i is not None])

    @field_validator("user_email")
    def check_user_email(cls, user_email: Optional[str]) -> Optional[str]:
        if user_email is None:
            return None
        if not re.search(r"^.*@((skbkontur)|(kontur))\.\w+$", user_email):
            raise ValueError("Почта не соответствует формату контуровской")
        return user_email

    @field_validator("return_date", "take_date", "reg_date", mode="before")
    def check_return_date(cls, return_date: Optional[str | datetime]) -> Optional[datetime]:
        if return_date is None:
            return None
        elif isinstance(return_date, str):
            if not re.search(r"^\d{2}.\d{2}.\d{4}$", return_date):
                raise ValueError("Дата не соответствует формату дд.мм.гггг")
            day, month, year = map(int, return_date.split("."))
            date = datetime(year, month, day)
        elif isinstance(return_date, datetime):
            date = return_date
        else:
            raise ValueError("Тип даты должен быть str или datetime")
        return date

    def __gt__(self, other: 'ResourceInfoDTO') -> bool:
        return self.name > other.name

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ResourceInfoDTO):
            return False
        return other.id == self.id
