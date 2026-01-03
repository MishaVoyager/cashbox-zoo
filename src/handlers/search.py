"""
Основной роутер для пользователя, позволяет искать ресурсы разными способами
"""
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from domain.models import Visitor
from helpers import tghelper as tg
from helpers.presentation import format_note
from helpers.texthelper import format_date
from helpers.tghelper import SEPARATOR_FOR_CALLBACK_DATA
from resources import strings
from service.services import ResourceService, VisitorService, RecordService

router = Router()


@router.message(Command("start"))
async def welcome_handler(
        message: Message,
        visitor: Visitor,
        command: CommandObject,
        resource_service: ResourceService,
        record_service: RecordService
) -> None:
    """Обрабатывает команду start. Если она с параметром (?start=something), то сразу ищет по ресурсам"""
    if not command.args:
        await welcome(message, visitor)
        return
    search_result = await resource_service.search(command.args.strip(), limit=200, max_id=10000)
    resources = search_result.unwrap()
    if len(resources) == 0:
        await message.answer(strings.not_found_msg)
    else:
        notes = ""
        for i in resources:
            get_result = await record_service.get_available_action(i.id, visitor.email)
            action = get_result.unwrap()
            notes += format_note(i, visitor, action)
        await message.answer(notes)


@router.message(Command("help"))
async def help_handler(message: Message, visitor: Visitor) -> None:
    await welcome(message, visitor)


async def welcome(message: Message, visitor: Visitor) -> None:
    """
    Выводит приветственное сообщение: для обычного пользователя одно,
    для админа - другое
    """
    if not visitor.is_admin:
        await message.answer(strings.welcome_msg)
    else:
        await message.answer(strings.admin_welcome_msg)


@router.message(Command("all"))
async def get_all_handler(message: Message, visitor: Visitor, resource_service: ResourceService,
                          record_service: RecordService) -> None:
    await search_resource(record_service, resource_service, message, 1, visitor, True)


async def search_resource(
        record_service: RecordService,
        resource_service: ResourceService,
        message: Message,
        page: int,
        visitor: Visitor,
        get_all: bool = False
) -> None:
    """Выводит для пользователя список ресурсов на определенной странице"""
    if get_all:
        query = ''
        get_all_result = await resource_service.get_all()
        resources = get_all_result.unwrap()
    else:
        query = message.text
        search_result = await resource_service.search(query, 200, 10000)
        resources = search_result.unwrap()
    if len(resources) == 0:
        await message.answer(strings.not_found_msg)
        return
    paginator = tg.Paginator(page, resources)
    notes = ""
    for i in paginator.get_objects_on_page():
        get_result = await record_service.get_available_action(i.id, visitor.email)
        action = get_result.unwrap()
        notes += format_note(i, visitor, action)
    await message.answer(
        text=paginator.result_message() + notes,
        reply_markup=paginator.create_keyboard("search_resource", query)
    )


@router.callback_query(F.data.startswith("search_resource"))
async def search_callback_handler(
        call: CallbackQuery,
        visitor: Visitor,
        resource_service: ResourceService,
        record_service: RecordService
) -> None:
    await call.answer()
    data = (str(call.data)).split(SEPARATOR_FOR_CALLBACK_DATA)
    page_number = int(data[1])
    search_users_by_query = len(data) >= 2
    if search_users_by_query:
        query = " ".join(data[2:])
        search_result = await resource_service.search(query, 200)
        resources = search_result.unwrap()
    else:
        query = ''
        get_all_result = await resource_service.get_all()
        resources = get_all_result.unwrap()
    paginator = tg.Paginator(page_number, resources)
    notes = ""
    for i in paginator.get_objects_on_page():
        get_result = await record_service.get_available_action(i.id,visitor.email)
        action = get_result.unwrap()
        notes += format_note(i, visitor, action)
    await call.message.edit_text(  # type: ignore
        text=paginator.result_message() + notes,
        reply_markup=paginator.create_keyboard("search_resource", query)
    )


@router.message(Command("wishlist"))
async def wishlist_handler(
        message: Message,
        visitor: Visitor,
        visitor_service: VisitorService,
        record_service: RecordService
) -> None:
    await get_wishlist(record_service, visitor_service, message, visitor, 1)


async def get_wishlist(
        record_service: RecordService,
        visitor_service: VisitorService,
        message: Message,
        visitor: Visitor,
        page: int,
        call: Optional[CallbackQuery] = None
) -> None:
    """Выводит для пользователя список из вишлиста на определенной странице"""
    wishlist_result = await visitor_service.get_queue(visitor)
    resources = wishlist_result.unwrap()
    if len(resources) == 0:
        await message.answer(strings.empty_wishlist)
        return
    paginator = tg.Paginator(page, resources)
    keyboard = paginator.create_keyboard("wishlist")
    notes = ""
    for i in paginator.get_objects_on_page():
        get_result = await record_service.get_available_action(i.id, visitor.email)
        action = get_result.unwrap()
        notes += format_note(i, visitor, action)
    text = paginator.result_message() + notes
    if call:
        await call.message.edit_text(text=text, reply_markup=keyboard)  # type: ignore
    else:
        await message.answer(text=text, reply_markup=keyboard)  # type: ignore


@router.callback_query(F.data.startswith("wishlist"))
async def wishlist_callback_handler(
        call: CallbackQuery,
        visitor: Visitor,
        record_service: RecordService,
        visitor_service: VisitorService
) -> None:
    await call.answer()
    data = str(call.data)
    page_number = int(data.split(SEPARATOR_FOR_CALLBACK_DATA)[1])
    await get_wishlist(record_service, visitor_service, call.message, visitor, page_number, call)


@router.message(Command("mine"))
async def get_mine_resources_handler(
        message: Message,
        visitor: Visitor,
        visitor_service: VisitorService,
        record_service: RecordService
) -> None:
    await get_mine_resources(record_service, visitor_service, message, visitor, 1)


async def get_mine_resources(
        record_service: RecordService,
        visitor_service: VisitorService,
        message: Message,
        visitor: Visitor,
        page: int,
        call: Optional[CallbackQuery] = None
) -> None:
    """Выводит список записанных на пользователя ресурсов на определенной странице"""
    get_taken_result = await visitor_service.get_taken_resources(visitor)
    resources = get_taken_result.unwrap()
    if len(resources) == 0:
        await message.answer(strings.user_have_no_device_msg)  # type: ignore
        return
    paginator = tg.Paginator(page, resources)
    keyboard = paginator.create_keyboard("mine")
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


@router.callback_query(F.data.startswith("mine"))
async def mine_callback_handler(
        call: CallbackQuery,
        visitor: Visitor,
        visitor_service: VisitorService,
        record_service: RecordService
) -> None:
    await call.answer()
    data = str(call.data)
    page_number = int(data.split(SEPARATOR_FOR_CALLBACK_DATA)[1])
    await get_mine_resources(record_service, visitor_service, call.message, visitor, page_number, call)


@router.message(Command("categories"))
async def get_categories_handler(message: Message, resource_service: ResourceService) -> None:
    get_categories_result = await resource_service.get_categories()
    if get_categories_result.is_failure or len(get_categories_result.unwrap()) == 0:
        await message.answer("Не найдена ни одна категория")
        return
    active_categories = get_categories_result.unwrap()
    await message.answer(
        text=strings.ask_category_msg,
        reply_markup=tg.get_inline_keyboard(active_categories, "categories")
    )


@router.callback_query(F.data.startswith("categories"))
async def category_callback_handler(
        call: CallbackQuery,
        visitor: Visitor,
        resource_service: ResourceService,
        record_service: RecordService
) -> None:
    await call.answer()
    data = str(call.data).split(SEPARATOR_FOR_CALLBACK_DATA)
    if len(data) <= 2:
        page = 1
        category = str(call.data).split(SEPARATOR_FOR_CALLBACK_DATA)[1]
    else:
        page = int(data[1])
        category = data[2]
    result = await resource_service.list_by_category_name(category)
    if result.is_failure or len(result.unwrap()) == 0:
        await call.message.answer(strings.not_found_msg)  # type: ignore
        return
    resources = result.unwrap()
    paginator = tg.Paginator(page, resources)
    keyboard = paginator.create_keyboard("categories", category)
    notes = ""
    for i in paginator.get_objects_on_page():
        get_result = await record_service.get_available_action(i.id, visitor.email)
        action = get_result.unwrap()
        notes += format_note(i, visitor, action)
    text = paginator.result_message() + notes
    await call.message.edit_text(text=text, reply_markup=keyboard)  # type: ignore


@router.message(F.text.regexp(r"\/history.+"))
async def edit_resource_handler(message: Message, visitor: Visitor, resource_service: ResourceService) -> None:
    if not visitor.is_admin:
        await message.answer(strings.not_admin_error_msg)
        return
    resource_id = int(message.text.removeprefix("/history"))
    result = await resource_service.get_finished_records(resource_id)
    resource_infos = result.unwrap()
    if len(resource_infos) == 0:
        await message.answer("Нет информации о прошлых записях")
    else:
        reply = f"История для {resource_infos[0].short_str()}: \n\n"
        for i in resource_infos:
            reply += f"{format_date(i.take_date)} - {format_date(i.return_date)}: {i.user_email}. Адрес: {i.address or 'не указан'}\n"
        await message.answer(reply)


@router.message(F.text)
async def search_resource_handler(message: Message, visitor: Visitor, resource_service: ResourceService,
                                  record_service: RecordService) -> None:
    text = message.text.strip()
    if text is None or text == "":
        await welcome_handler(message)
        return
    await search_resource(record_service, resource_service, message, 1, visitor, False)
