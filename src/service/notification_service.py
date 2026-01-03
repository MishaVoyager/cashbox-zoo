import logging
from aiogram import Bot
from aiogram.types import ReplyKeyboardRemove

from configs.config import Settings
from database.uow import UnitOfWork
from domain.models import Resource
from domain.resource_info import ResourceInfoDTO
from resources import strings


class NotificationService:
    def __init__(self, unit_of_work: UnitOfWork):
        self.unit_of_work = unit_of_work
        self.bot = Bot(token=Settings().token)

    async def notify_user_about_take(self, user_email: str, resource: Resource | ResourceInfoDTO) -> None:
        """Отправляет уведомление пользователю о том, что на него записано устройство"""
        async with self.unit_of_work as uow:
            visitor = await uow.visitors.get(user_email)
            if visitor and visitor.chat_id:
                await self.bot.send_message(
                    chat_id=visitor.chat_id,
                    text=strings.notify_user_about_take_msg(resource),
                    reply_markup=ReplyKeyboardRemove()
                )
                logging.info(f"Пользователь {repr(visitor)} уведомлен о записи устройства {repr(resource)}")

    async def notify_next_user_about_take(self, user_email: str, resource: Resource | ResourceInfoDTO) -> None:
        """Отправляет уведомление следующему пользователю в очереди о том, что устройство освободилось"""
        async with self.unit_of_work as uow:
            visitor = await uow.visitors.get(user_email)
            if visitor and visitor.chat_id:
                await self.bot.send_message(
                    chat_id=visitor.chat_id,
                    text=strings.notify_next_user_about_take_msg(resource),
                    reply_markup=ReplyKeyboardRemove()
                )
                logging.info(f"Пользователь {repr(visitor)} уведомлен о получении устройства {repr(resource)}")

    async def notify_user_about_return(self, user_email: str, resource: Resource | ResourceInfoDTO) -> None:
        """Отправляет уведомление пользователю о том, что устройство списано с него"""
        async with self.unit_of_work as uow:
            visitor = await uow.visitors.get(user_email)
            if visitor and visitor.chat_id:
                await self.bot.send_message(
                    chat_id=visitor.chat_id,
                    text=strings.notify_user_about_return_msg(resource),
                    reply_markup=ReplyKeyboardRemove()
                )
                logging.info(f"Пользователь {repr(visitor)} уведомлен о списании устройства {repr(resource)}") 