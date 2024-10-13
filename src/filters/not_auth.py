"""
Кастомный фильтр, который проверяет, есть ли в БД такой посетитель.
Если нет - в роутере auth проводим его авторизацию.
"""

from typing import Union, Dict, Any

from aiogram.filters import BaseFilter
from aiogram.types import Message

from database.models import Visitor


class NotAuthFilter(BaseFilter):
    async def __call__(self, message: Message) -> Union[bool, Dict[str, Any]]:
        return not await Visitor.is_exist(message.chat.id)
