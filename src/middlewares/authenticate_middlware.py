import logging
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject, ReplyKeyboardRemove, CallbackQuery

from domain.models import Visitor
from helpers import staffhelper
from resources import strings
from service.services import VisitorService


class Auth(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: Message | CallbackQuery,
            data: Dict[str, Any]
    ) -> Any:
        visitor_service: VisitorService = data["visitor_service"]

        if isinstance(event, Message):
            result = await visitor_service.get_by_chat_id(event.chat.id)
            if result.is_failure:
                await login(event, visitor_service)
                return
            visitor = result.unwrap()
        elif isinstance(event, CallbackQuery):
            result = await visitor_service.get_by_chat_id(event.message.chat.id)
            if result.is_failure:
                await login(event.message, visitor_service)
                return
            visitor = result.unwrap()
        else:
            return
        data["visitor"] = visitor
        return await handler(event, data)


async def login(message: Message, visitor_service: VisitorService) -> None:
    username = message.from_user.username
    if not username:
        await message.answer(strings.should_be_username_msg)
        return
    emails = await staffhelper.search_emails(username)
    if emails is None:
        await message.answer(strings.unexpected_action_msg)
        logging.warning(f"Ошибка при запросе в Стафф для пользователя {username}")
        return
    if len(emails) == 0:
        await message.answer(f"{strings.Emoji.ALIEN.value}")
        await message.answer(strings.no_telegram_in_staff_msg)
        logging.info(f"В Стаффе не найден телеграм пользователя {username}")
        return
    if len(emails) > 1:
        logging.warning(f"Для {username} найдено несколько почт: " + ", ".join(emails))
    new_visitor = Visitor(
        email=emails[0],
        chat_id=message.chat.id,
        user_id=message.from_user.id,
        full_name=message.from_user.full_name,
        username=message.from_user.username
    )
    await visitor_service.auth(new_visitor)
    await message.answer(
        text=f"{strings.Emoji.ZOO.value}",
        reply_markup=ReplyKeyboardRemove()
    )
    await message.answer(
        text=strings.auth_message(new_visitor.email, new_visitor.is_admin),
        reply_markup=ReplyKeyboardRemove()
    )
