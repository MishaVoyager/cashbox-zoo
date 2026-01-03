import logging
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject, CallbackQuery


class TryFilterOuter(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: Message | CallbackQuery,
            data: Dict[str, Any]
    ) -> Any:
        result = await handler(event, data)
        if hasattr(result, 'name') and result.name == "UNHANDLED":
            message = event if isinstance(event, Message) else event.message
            state = data['raw_state'] if 'raw_state' in data else "None"
            info = f"Состояние: {state}. Тип сообщения: {message.content_type}. Сообщение: {message.text}"
            logging.error(
                f"У @{message.from_user.username} ({(message.from_user.full_name)}) не обработалось событие. {info}")
            await message.answer("Не удалось обработать ваше сообщение. Попробуйте снова")
