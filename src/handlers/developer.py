"""
Роутер для разработчика приложения.
Позволяет получать логи из файлов и взаимодействовать с БД.
Действия защищаются паролем - значением определенной переменной среды.
"""

import logging
import os
from datetime import datetime
from io import StringIO, BytesIO
from typing import Optional, List

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import BufferedInputFile, ReplyKeyboardMarkup, CallbackQuery
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram_calendar import SimpleCalendarCallback
from openpyxl.workbook import Workbook

from configs.config import Settings
from domain.models import Visitor, Record
from domain.resource_info import ResourceInfoDTO
from helpers import tghelper as tg
from helpers.fsmhelper import CANCEL_KEYBOARD, fill_date_from_calendar
from helpers.presentation import format_note
from helpers.tghelper import Paginator, SEPARATOR_FOR_CALLBACK_DATA, start_calendar, nameof
from middlewares.authorize_middleware import Authorize
from resources import strings
from service.database_service import DatabaseService
from service.services import ResourceService, RecordService

LOGS_FOLDER = os.path.join(os.curdir, "logs")
CURRENT_LOG_NAME = "cashbox_zoo.log"
LOG_PATH = os.path.join(LOGS_FOLDER, CURRENT_LOG_NAME)


class InfoFSM(StatesGroup):
    choosing = State()
    calendar = State()
    confirm_delete_free_devices = State()
    confirm_delete_db = State()
    confirm_get_revisions = State()


router = Router()
router.message.middleware(Authorize())
router.callback_query.middleware(Authorize())


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


def get_options_keyboard() -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру с доступными опциями"""
    buttons = [
        "Занятые устройства",
        "Скачать табличку",
        "Узнать про миграции",
        "Удалить незанятые",
        "Удалить базу",
        "Потестить календарь",
        "Выйти"
    ]
    return tg.get_reply_keyboard(buttons)


@router.message(Command("info"))
async def info_handler(message: Message, state: FSMContext) -> None:
    await state.set_state(InfoFSM.choosing)
    await message.answer(
        text="Что хотите?",
        reply_markup=get_options_keyboard()
    )


async def get_devices_excel(resource_infos: List[ResourceInfoDTO]) -> Workbook:
    """Формирует excel workbook со списком ресурсов"""
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
    wb = Workbook()
    ws = wb.active
    ws.append(first_row)
    for info in resource_infos:
        ws.append(info.values())
    return wb


async def convert_string_io_to_bytes(text_file: StringIO) -> bytes:
    return text_file.read().encode(encoding="cp1251")


async def convert_workbook_to_bytes(wb: Workbook) -> bytes:
    virtual_workbook = BytesIO()
    wb.save(virtual_workbook)
    return virtual_workbook.getvalue()


@router.message(InfoFSM.choosing)
async def choosing_handler(
        message: Message,
        visitor: Visitor,
        state: FSMContext,
        resource_service: ResourceService,
        record_service: RecordService
) -> None:
    text = message.text.strip()
    if text == "Занятые устройства":
        await get_taken_resources(resource_service, record_service, message, visitor, 1)
    elif text == "Скачать табличку":
        get_all_result = await resource_service.get_all()
        resource_infos = get_all_result.unwrap()
        wb = await get_devices_excel(resource_infos)
        file = await convert_workbook_to_bytes(wb)
        input_file = BufferedInputFile(file, "devices.xlsx")
        await message.reply_document(input_file)
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
    elif text == "Потестить календарь":
        await state.set_state(InfoFSM.calendar)
        now_date = datetime.now()
        await message.answer(
            f"Текущий год: {now_date.year}.\nТекущий месяц: {now_date.month}.\nДата в целом: {now_date}")
        await message.answer(
            text="Выберите дату",
            reply_markup=await start_calendar()
        )
    elif text == "Выйти":
        await state.clear()
        await message.answer("Вы вышли из режима info", reply_markup=ReplyKeyboardRemove())
    else:
        await message.answer("Выберите из списка вариантов")


async def get_taken_resources(
        resource_service: ResourceService,
        record_service: RecordService,
        message: Message,
        visitor: Visitor,
        page: int,
        call: Optional[CallbackQuery] = None
) -> None:
    get_taken_result = await record_service.get_all_taken()
    resource_infos = get_taken_result.unwrap()
    if len(resource_infos) == 0:
        await message.answer("Ни одного устройства не записано на пользователей. Все в домике")  # type: ignore
        return
    paginator = Paginator(page, resource_infos)
    keyboard = paginator.create_keyboard("taken")
    notes = ""
    for i in paginator.get_objects_on_page():
        get_result = await record_service.get_available_action(i.id, visitor.email)
        action = get_result.unwrap()
        notes += format_note(i, visitor, action)
    text = paginator.result_message() + notes
    if not call:
        await message.answer(text=text, reply_markup=keyboard)  # type: ignore
    else:
        await call.message.edit_text(text=text, reply_markup=keyboard)  # type: ignore


@router.callback_query(F.data.startswith("taken"))
async def taken_resouces_callback_handler(
        call: CallbackQuery,
        visitor: Visitor,
        resource_service: ResourceService,
        record_service: RecordService
) -> None:
    await call.answer()
    data = str(call.data)
    page_number = int(data.split(SEPARATOR_FOR_CALLBACK_DATA)[1])
    await get_taken_resources(resource_service, record_service, call.message, visitor, page_number, call)  # type: ignore


@router.message(InfoFSM.confirm_delete_db)
async def confirm_delete_db_handler(message: Message, state: FSMContext, visitor: Visitor,
                                    database_service: DatabaseService) -> None:
    if not (await check_password_and_answer(visitor, message, state)):
        return
    await database_service.drop_base()
    await state.clear()
    await message.answer(
        text="БД успешно удалена, для повторной инициализации перезапустите приложение",
        reply_markup=ReplyKeyboardRemove()
    )
    logging.warning(f"Пользователь {repr(visitor)} успешно удалил БД")


@router.message(InfoFSM.confirm_delete_free_devices)
async def confirm_delete_free_devices_handler(
        message: Message,
        state: FSMContext,
        visitor: Visitor,
        resource_service: ResourceService

) -> None:
    if not (await check_password_and_answer(visitor, message, state)):
        return
    await resource_service.delete_all_free()
    await state.clear()
    await message.answer(
        text="Все незанятые устройства успешно удалены. Занятые - освободите вручную",
        reply_markup=ReplyKeyboardRemove()
    )
    logging.warning(f"Пользователь {repr(visitor)} успешно удалил все незанятые ресурсы")


@router.message(InfoFSM.confirm_get_revisions)
async def confirm_get_revisions_handler(
        message: Message,
        state: FSMContext,
        visitor: Visitor,
        database_service: DatabaseService
) -> None:
    if not (await check_password_and_answer(visitor, message, state)):
        return
    text_file = await database_service.get_revisions_from_cli()
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
    logging.warning(f"Пользователь {repr(visitor)} получил инфу про миграции")


async def check_password_and_answer(visitor: Visitor, message: Message, state: FSMContext) -> bool:
    """Проверяет, соответствует ли пароль переменной среды. Сообщает пользователю об ошибке"""
    admin_pass = Settings().zoo_admin_pass
    state_name = await state.get_state()
    if admin_pass is None:
        await message.answer(
            text=f"Не удалось выполнить {state_name}: не задан пароль админа",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()
        logging.error(f"Пользователю {repr(visitor)} не удалось выполнить {state_name}: не задан пароль админа")
        return False
    if message.text != admin_pass:
        await message.answer(
            text="Некорректный пароль. Введите его снова или нажмите Отменить",
            reply_markup=CANCEL_KEYBOARD
        )
        logging.warning(f"Пользователю {repr(visitor)} не удалось выполнить {state_name}: неправильный пароль")
        return False
    return True


@router.callback_query(SimpleCalendarCallback.filter(), StateFilter(InfoFSM.calendar))
async def calendar_test_handler(call: CallbackQuery, callback_data: CallbackData, state: FSMContext) -> None:
    date = await fill_date_from_calendar(
        call,
        callback_data,
        state,
        None,
        nameof(Record.return_date),
        "Дата успешно выбрана",
        CANCEL_KEYBOARD,
        False
    )
    await call.message.answer(text=f"Выбранная дата: {date}", reply_markup=ReplyKeyboardRemove())
    await call.message.answer(text=f"Колбэк: {callback_data}")
