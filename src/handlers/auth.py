"""
Роутер для авторизации. В случае нашего бота - просим ввести пользователя контуровскую почту.
"""
import logging

from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.types import Message, ReplyKeyboardRemove

from database.models import Visitor
from filters import not_auth
from handlers import strings
from helpers import staffhelper

router = Router()
router.message.filter(not_auth.NotAuthFilter())


@router.message(StateFilter(None))
async def login(message: Message) -> None:
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
        await message.answer(strings.no_telegram_in_staff_msg)
        logging.info(f"В Стаффе не найден телеграм пользователя {username}")
        return
    if len(emails) > 1:
        logging.warning(f"Для {username} найдено несколько почт: " + ", ".join(emails))
    user = await Visitor.auth(emails[0], message)
    await message.answer(
        text=strings.auth_message(user.email, user.is_admin),
        reply_markup=ReplyKeyboardRemove()
    )
