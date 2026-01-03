"""
Модуль для работы с телеграмом, в первую очередь - для создания клавиатур.

Classes
--------
Paginator
    Дает список объектов на определенной странице и соответствующую инлайн-клавиатуру.
    Методы класса неплохо покрыты тестами.
"""

import math
from datetime import datetime
from enum import StrEnum
from typing import Optional, BinaryIO, Any

from aiogram import types
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram_calendar import SimpleCalendar

import helpers.texthelper as texthelper
from configs.config import Settings
from domain.models import Visitor

SEPARATOR_FOR_CALLBACK_DATA: str = ','

locale = Settings().locale_for_calendar


def get_calendar_ru() -> SimpleCalendar:
    return SimpleCalendar(show_alerts=True, locale=locale, cancel_btn="Отмена", today_btn="Этот месяц")


async def start_calendar() -> InlineKeyboardMarkup:
    now = datetime.now()
    calendar = get_calendar_ru()
    return await calendar.start_calendar(now.year, now.month)


async def get_file_from_tg(message: Message) -> BinaryIO:
    """Достает из сообщения файл и загружает его в память"""
    original_file = await message.bot.get_file(message.document.file_id)
    in_memory_file = await message.bot.download(file=original_file)  # type: ignore
    in_memory_file.name = original_file.file_path
    return in_memory_file


def get_reply_keyboard(elements: list[str]) -> ReplyKeyboardMarkup:
    """Возвращает стандартную клавиатуру с вариантами ответа"""
    builder = ReplyKeyboardBuilder()
    for element in elements:
        builder.button(text=f"{element}")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def get_inline_keyboard(elements: list[str], callback_data: str) -> InlineKeyboardMarkup:
    """Возвращает стандартную инлайн-клавиатуру"""
    builder = InlineKeyboardBuilder()
    for element in elements:
        builder.row(types.InlineKeyboardButton(
            text=f"{element}",
            callback_data=f"{callback_data}{SEPARATOR_FOR_CALLBACK_DATA}{element}")
        )
    builder.adjust(2)
    return builder.as_markup()


class Paginator:
    """Класс, который по списку объектов формирует срез и клавиатуру"""

    def __repr__(self) -> str:
        return f"Paginator(page={self.page}, " \
               f"visible_results={self.visible_results}, " \
               f"page_elements={self.page_elements}, " \
               f"pages={self.pages}, " \
               f"len objects={len(self.objects)})"

    def __str__(self) -> str:
        return f"Пагинатор для страницы {self.page}: " \
               f"количество элементов {self.page_elements}, " \
               f"количество видимых страниц {self.visible_results}"

    def __init__(self, page: int, objects: list, visible_results: int = 5, page_elements: int = 5):
        self.objects = objects
        self.pages = math.ceil(len(objects) / visible_results)
        self.visible_results = visible_results
        self.page_elements = page_elements
        self.page = page

    def get_pages_numbers(self) -> tuple[Optional[int], ...]:
        """Возвращает кортеж номеров страниц, например (1, 2, 3) или (None, None, None)"""
        if self.page > self.pages:
            raise AssertionError("Номер страницы не может быть выше максимального")
        if self.page == self.pages == 1:
            return tuple([None] * self.page_elements)
        result = [i + self.page for i in range(self.page_elements)]
        while result[-1] > min(self.pages, self.page + int(self.page_elements / 2)) and result[-1] > self.page_elements:
            result = list(map(lambda x: x - 1, result))
        return tuple(map(lambda x: x if x <= self.pages else None, result))

    def create_keyboard(self, page_handle: str, query: str = '') -> InlineKeyboardMarkup:
        """Формирует клавиатуру с определенными номерами страниц и page_handle для коллбэка"""
        builder = InlineKeyboardBuilder()
        page_numbers = self.get_pages_numbers()
        [self._create_page_button(builder, number, page_handle, query) for number in page_numbers if number]
        builder.adjust(self.page_elements)
        return builder.as_markup()

    def _create_page_button(self, builder: InlineKeyboardBuilder, number: int,
                            page_handle: str, query: str = '') -> InlineKeyboardBuilder:
        """Формирует кнопку с цифрой"""
        builder.row(types.InlineKeyboardButton(
            text=f"{number}" if number != self.page else f"-{number}-",
            callback_data=f"{page_handle}{SEPARATOR_FOR_CALLBACK_DATA}{number}{SEPARATOR_FOR_CALLBACK_DATA}{query}"))
        return builder

    def get_objects_on_page(self) -> list:
        """Возвращает список объектов на странице"""
        left, right = self.get_array_indexes()
        return self.objects[left: right + 1]

    def get_array_indexes(self) -> tuple[int, int]:
        """Возвращает индексы левой и правой границы для объектов на странице"""
        left_index = 0 + self.visible_results * (self.page - 1)
        right_index = min((self.visible_results - 1) + self.visible_results * (self.page - 1), len(self.objects) - 1)
        return left_index, right_index

    def result_message(self) -> str:
        """Формирует сообщение о результате поиска"""
        count = len(self.objects)
        return f"Всего найден{texthelper.get_word_ending(count, ['', 'о', 'о'])} " \
               f"{count} результат{texthelper.get_word_ending(count, ['', 'а', 'ов'])}:\r\n\r\n"


class ActionsOnVisitors(StrEnum):
    """Действия над пользователями"""
    COMMENT = "Изменить коммент: /comment"
    EMAIL = "Изменить email: /email"
    DELETE = "Удалить: /delete"
    USER_HISTORY = "История: /user_history"


def render_visitors(visitors: list[Visitor]) -> str:
    """Формирует текст со списком пользователей и доступными действиями"""
    result = ''
    for visitor in visitors:
        result += f"{str(visitor)}\r\n{visitor_actions_str(visitor)}\r\n\r\n"
    return result


def visitor_actions_str(visitor: Visitor) -> str:
    """Формирует текст про действия над пользователем"""
    return '\r\n'.join([f'{action.value}{visitor.id}' for action in ActionsOnVisitors])


def nameof(field: Any) -> str:
    """
    Возвращает название аттрибута класса.
    При написании аттрибута строкой можно ошибиться, например, написать "email".
    Эта ситуация исключена, если писать nameof(Resource.user_email)
    """
    return str(field).split(".")[1]

# async def start_webhook(bot: Bot, dp: Dispatcher, webhook_path: str, webhook_secret: str, host: str, port: int) -> None:
#     """Запускает приложение в режиме вебкуха"""
#     from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
#     from aiohttp import web
#     webhook_route = "/webhook"
#     webhook_url = f"{webhook_path}{webhook_route}"
#     logging.info(f"Телеграму передан адрес вебхука: {webhook_url}")
#     await bot.set_webhook(webhook_url, secret_token=webhook_secret)
#     app = web.Application()
#     webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot,
#                                                     secret_token=webhook_secret)
#     webhook_requests_handler.register(app, path=webhook_route)
#     setup_application(app, dp, bot=bot)
#     logging.info(
#         f"Приложение запустилось на сервере. Хост: {host}, порт: {port}. "
#         f"URL вебхука: {webhook_url}")
#     await web._run_app(app, host=host, port=port)
