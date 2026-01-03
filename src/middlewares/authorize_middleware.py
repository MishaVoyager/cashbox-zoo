from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject, CallbackQuery

from resources import strings


class Authorize(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: Message | CallbackQuery,
            data: Dict[str, Any]
    ) -> Any:
        visitor = data["visitor"]
        if not visitor.is_admin:
            if isinstance(event, Message):
                await event.answer(strings.not_found_msg)
                return
            elif isinstance(event, CallbackQuery):
                await event.message.answer(strings.not_found_msg)
                return
            else:
                return
        return await handler(event, data)
