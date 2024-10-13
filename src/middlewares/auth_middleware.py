"""
Пример кастомного мидлваря. По факту в проекте не используется.
"""

from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message

from database.models import Visitor


class AuthMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,  # type: ignore[override]
            data: Dict[str, Any]
    ) -> Any:
        data["authorized"] = await Visitor.is_exist(event.chat.id)
        return await handler(event, data)
