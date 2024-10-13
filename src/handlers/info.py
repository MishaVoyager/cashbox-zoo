"""
Роутер для разработчика приложения.
Позволяет получать логи из файлов и взаимодействовать с БД.
Действия защищаются паролем - значением определенной переменной среды.
"""

import csv
import logging
import os
from datetime import datetime
from io import StringIO

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import BufferedInputFile
from aiogram.types import Message, FSInputFile, ReplyKeyboardRemove

from configs.config import Settings
from database import dbhelper
from database.models import Visitor, Resource, Record
from handlers import strings
from helpers import tghelper as tg
from helpers.fsmhelper import CANCEL_KEYBOARD

LOGS_FOLDER = os.path.join(os.curdir, "logs")
CURRENT_LOG_NAME = "cashbox_zoo.log"
LOG_PATH = os.path.join(LOGS_FOLDER, CURRENT_LOG_NAME)


class InfoFSM(StatesGroup):
    choosing = State()
    confirm_delete_free_devices = State()
    confirm_delete_db = State()
    confirm_download_db = State()
    confirm_get_revisions = State()


router = Router()


def get_db_files() -> list[str]:
    """Возвращает список файлов с разрешением .db в текущей директории"""
    files = []
    for (_, _, filenames) in os.walk(os.curdir):
        files = [name for name in filenames if ".db" in name]
    return files


def get_log_files() -> list[str]:
    """
    Возвращает список файлы логов в директории с логами
    Не используется, если логи пишутся не в файлы, а в вывод
    """
    files = []
    for (_, _, filenames) in os.walk(LOGS_FOLDER):
        files = [os.path.join(LOGS_FOLDER, name) for name in filenames if ".log" in name]
    return files


def get_options_keyboard():
    """Возвращает клавиатуру с доступными опциями"""
    buttons = [
        "Cкачать табличку",
        "Скачать объекты из базы",
        "Узнать про миграции",
        "Удалить незанятые",
        "Удалить базу",
        "Выйти"
    ]
    if Settings().write_logs_in_file:
        buttons += ["Последний лог", "Все логи"]
    return tg.get_reply_keyboard(buttons)


@router.message(Command("info"))
async def info_handler(message: Message, state: FSMContext) -> None:
    user = await Visitor.get_current(message.chat.id)
    if not user.is_admin:
        await message.answer(strings.not_found_msg)
        return
    await state.set_state(InfoFSM.choosing)
    await message.answer(
        text="Что хотите?",
        reply_markup=get_options_keyboard()
    )


async def get_devices_csv() -> StringIO:
    """Формирует csv со списком ресурсов"""
    resources = await Resource.get_all(1000)
    first_row = [
        "Айди",
        "Название",
        "Категория",
        "Артикул",
        "Дата регистрации",
        "Прошивка",
        "Комментарий",
        "Электронная почта",
        "Место устройства",
        "Дата возврата"
    ]
    text = StringIO()
    csv.writer(text).writerow(first_row)
    for resource in resources:
        resource_scv = await resource.get_csv_value()
        csv.writer(text).writerow(resource_scv)
    text.seek(0)
    return text


@router.message(InfoFSM.choosing)
async def choosing_handler(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    if text == "Последний лог":
        await message.reply_document(FSInputFile(LOG_PATH))
    elif text == "Все логи":
        file_names = get_log_files()
        if len(file_names) == 0:
            logging.error("В папке не найдены логи!")
        for file_name in file_names:
            await message.reply_document(FSInputFile(file_name))
    elif text == "Cкачать табличку":
        text_file = await get_devices_csv()
        file = text_file.read().encode(encoding="cp1251")
        input_file = BufferedInputFile(file, "devices.csv")
        await message.reply_document(input_file)
    elif text == "Скачать объекты из базы":
        await state.set_state(InfoFSM.confirm_download_db)
        await message.answer(
            text=strings.password_required_msg,
            reply_markup=CANCEL_KEYBOARD
        )
    elif text == "Удалить незанятые":
        await state.set_state(InfoFSM.confirm_delete_free_devices)
        await message.answer(
            text=strings.password_required_msg,
            reply_markup=CANCEL_KEYBOARD
        )
    elif text == "Удалить базу":
        await state.set_state(InfoFSM.confirm_delete_db)
        await message.answer(
            text=strings.password_required_msg,
            reply_markup=CANCEL_KEYBOARD
        )
    elif text == "Узнать про миграции":
        await state.set_state(InfoFSM.confirm_get_revisions)
        await message.answer(
            text=strings.password_required_msg,
            reply_markup=CANCEL_KEYBOARD
        )
    elif text == "Выйти":
        await state.clear()
        await message.answer("Вы вышли из режима info", reply_markup=ReplyKeyboardRemove())
    else:
        await message.answer("Выберите из списка вариантов")


@router.message(InfoFSM.confirm_delete_db)
async def confirm_delete_db_handler(message: Message, state: FSMContext) -> None:
    user = await Visitor.get_current(message.chat.id)
    if not (await check_password_and_answer(user, message, state)):
        return
    await dbhelper.drop_base()
    await state.clear()
    await message.answer(
        text="БД успешно удалена, для повторной инициализации перезапустите приложение",
        reply_markup=ReplyKeyboardRemove()
    )
    logging.warning(f"Пользователь {repr(user)} успешно удалил БД")


@router.message(InfoFSM.confirm_delete_free_devices)
async def confirm_delete_free_devices_handler(message: Message, state: FSMContext) -> None:
    user = await Visitor.get_current(message.chat.id)
    if not (await check_password_and_answer(user, message, state)):
        return
    await dbhelper.delete_all_free_resources()
    await state.clear()
    await message.answer(
        text="Все незанятые устройства успешно удалены. Занятые - освободите вручную",
        reply_markup=ReplyKeyboardRemove()
    )
    logging.warning(f"Пользователь {repr(user)} успешно удалил все незанятые ресурсы")


@router.message(InfoFSM.confirm_download_db)
async def confirm_download_db_handler(message: Message, state: FSMContext) -> None:
    user = await Visitor.get_current(message.chat.id)
    if not (await check_password_and_answer(user, message, state)):
        return
    resources = await Resource.get_as_string_io(1000)
    visitors = await Visitor.get_as_string_io(1000)
    records = await Record.get_as_string_io(1000)
    for text_file in resources, visitors, records:
        if len(text_file.getvalue()) == 0:
            await message.answer(f"Нет объектов в таблице {text_file.name}")
            continue
        file = text_file.read().encode(encoding="utf-8")
        input_file = BufferedInputFile(file, f"{datetime.now().strftime('%d-%m-%Y')}-{text_file.name}.txt")
        await message.reply_document(input_file)
    await state.clear()
    await message.answer(
        text=f"Вам отправлены файлы с данными из БД от {datetime.now()}",
        reply_markup=ReplyKeyboardRemove()
    )
    logging.warning(f"Пользователь {repr(user)} скачал информацию из БД")


@router.message(InfoFSM.confirm_get_revisions)
async def confirm_get_revisions_handler(message: Message, state: FSMContext) -> None:
    user = await Visitor.get_current(message.chat.id)
    if not (await check_password_and_answer(user, message, state)):
        return
    text_file = await dbhelper.get_revisions_as_string_io()
    if len(text_file.getvalue()) == 0:
        await message.answer("В БД отсутствуют миграции")
    else:
        file = text_file.read().encode(encoding="utf-8")
        input_file = BufferedInputFile(file, f"{datetime.now().strftime('%d-%m-%Y')}-{text_file.name}.txt")
        await message.reply_document(input_file)
    await state.clear()
    await message.answer(
        text=f"Вам отправлена инфа о миграциях от алембика на момент: {datetime.now()}",
        reply_markup=ReplyKeyboardRemove()
    )
    logging.warning(f"Пользователь {repr(user)} получил инфу про миграции")


async def check_password_and_answer(user: Visitor, message: Message, state: FSMContext) -> bool:
    """Проверяет, соответствует ли пароль переменной среды. Сообщает пользователю об ошибке"""
    admin_pass = Settings().zoo_admin_pass
    state_name = await state.get_state()
    if admin_pass is None:
        await message.answer(
            text=f"Не удалось выполнить {state_name}: не задан пароль админа",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()
        logging.error(f"Пользователю {repr(user)} не удалось выполнить {state_name}: не задан пароль админа")
        return False
    if message.text != admin_pass:
        await message.answer(
            text="Некорректный пароль. Введите его снова или нажмите Отменить",
            reply_markup=CANCEL_KEYBOARD
        )
        logging.warning(f"Пользователю {repr(user)} не удалось выполнить {state_name}: неправильный пароль")
        return False
    return True
