"""
Модуль с методами проверки ресурса на содержание конкретных полей, уникальность и т.д

Classes
--------
ResourceError
    Енам содержит список ошибок при обработке ресурса и текстовое описание ошибки
"""
import re
from datetime import datetime
from re import Match
from typing import Optional

from resources.strings import ResourceError


def check_date(value: Optional[str], future_date: bool) -> bool:
    """Проверяет дату для устройства"""
    if not re.search(r"^\d{2}.\d{2}.\d{4}$", value):
        return False
    day, month, year = map(int, value.split("."))
    try:
        date = datetime(year, month, day)
    except ValueError:
        return False
    if future_date and date.date() < datetime.now().date():
        return False
    return True


def try_convert_to_ddmmyyyy(date: str) -> Optional[datetime]:
    """
    Конвертирует текстовую строку в формате dd.mm.yyyy -
    в datetime, либо возвращает value_error
    """
    if not re.search(r"^\d{2}.\d{2}.\d{4}$", date):
        return None
    day, month, year = map(int, date.split("."))
    try:
        return datetime(year, month, day)
    except ValueError:
        return None


def is_kontur_email(email: str) -> Optional[Match]:
    """Проверяет, что email - контуровский"""
    return re.search(r"^.*@((skbkontur)|(kontur))\.\w+$", email)


def is_paste_date(date: datetime) -> bool:
    """Проверяет, что дата из прошлого"""
    return date.date() < datetime.now().date()


def format_errors(indexes_with_errors: dict[int, list[ResourceError]]) -> str:
    """Выводит сообщение про ошибки в определенных строках"""
    errors_text = ""
    for row, errors in indexes_with_errors.items():
        errors_text += f"В строке {row}:\r\n" + "\r\n".join([i.value for i in errors]) + "\r\n\r\n"
    return errors_text
