"""
Маленький вспомогательный модуль для работы с текстом
"""
from datetime import datetime


def get_word_ending(count: int, variants: list[str]) -> str:
    """
    Возвращает окончание слова в зависимости от количества.
    :variants - варианты окончания, первое - например, для количества 1, второе для 2, третье для 5
    """
    count = count % 100
    if 11 <= count <= 19:
        return variants[2]
    count = count % 10
    if count == 1:
        return variants[0]
    elif count in [2, 3, 4]:
        return variants[1]
    return variants[2]


def format_date(date: datetime) -> str:
    return date.strftime('%d.%m.%Y')
