"""
Основной роутер для пользователя, позволяет искать ресурсы разными способами
"""
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from database import dbhelper
from database.models import Resource, Visitor
from handlers import strings
from helpers import tghelper as tg

router = Router()


@router.message(Command("start"))
async def welcome_handler(message: Message, command: CommandObject) -> None:
    """Обрабатывает команду start. Если она с параметром (?start=something), то сразу ищет по ресурсам"""
    if not command.args:
        await welcome(message)
        return
    resources = await Resource.search(command.args.strip())
    if len(resources) == 0:
        await message.answer(strings.not_found_msg)
    else:
        await message.answer(await dbhelper.format_notes(resources, message.chat.id))


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    await welcome(message)


async def welcome(message: Message) -> None:
    """
    Выводит приветственное сообщение: для обычного пользователя одно,
    для админа - другое
    """
    user: Visitor = await Visitor.get_current(message.chat.id)
    if not user.is_admin:
        await message.answer(strings.welcome_msg)
    else:
        await message.answer(strings.admin_welcome_msg)


@router.message(Command("all"))
async def get_all_handler(message: Message) -> None:
    await search_resource(message, 1, True)


async def search_resource(message: Message, page: int, get_all: bool = False) -> None:
    """Выводит для пользователя список ресурсов на определенной странице"""
    if get_all:
        query = ''
        resources = await Resource.get_all()
    else:
        query = message.text
        resources = await Resource.search(query)
    if len(resources) == 0:
        await message.answer(strings.not_found_msg)
        return
    paginator = tg.Paginator(page, resources)
    notes = await dbhelper.format_notes(paginator.get_objects_on_page(), message.chat.id)
    await message.answer(
        text=paginator.result_message() + notes,
        reply_markup=paginator.create_keyboard("search_resource", query)
    )


@router.callback_query(F.data.startswith("search_resource"))
async def search_callback_handler(call: CallbackQuery) -> None:
    await call.answer()
    data = (str(call.data)).split()
    page_number = int(data[1])
    search_users_by_query = len(data) >= 2
    if search_users_by_query:
        query = " ".join(data[2:])
        resources = await Resource.search(query)
    else:
        query = ''
        resources = await Resource.get_all()
    paginator = tg.Paginator(page_number, resources)
    notes = await dbhelper.format_notes(paginator.get_objects_on_page(), call.message.chat.id)
    await call.message.edit_text(  # type: ignore
        text=paginator.result_message() + notes,
        reply_markup=paginator.create_keyboard("search_resource", query)
    )


@router.message(Command("wishlist"))
async def wishlist_handler(message: Message) -> None:
    await get_wishlist(message, 1)


async def get_wishlist(message: Message, page: int, call: Optional[CallbackQuery] = None) -> None:
    """Выводит для пользователя список из вишлиста на определенной странице"""
    user = await Visitor.get_current(message.chat.id)
    resources = await dbhelper.get_wishlist(user)
    if len(resources) == 0:
        await message.answer(strings.empty_wishlist)
        return
    paginator = tg.Paginator(page, resources)
    keyboard = paginator.create_keyboard("wishlist")
    notes = await dbhelper.format_notes(paginator.get_objects_on_page(), message.chat.id)
    text = paginator.result_message() + notes
    if call:
        await call.message.edit_text(text=text, reply_markup=keyboard)  # type: ignore
    else:
        await message.answer(text=text, reply_markup=keyboard)  # type: ignore


@router.callback_query(F.data.startswith("wishlist"))
async def wishlist_callback_handler(call: CallbackQuery) -> None:
    await call.answer()
    data = str(call.data)
    page_number = int(data.split()[1])
    await get_wishlist(call.message, page_number, call)  # type: ignore


@router.message(Command("mine"))
async def get_mine_resources_handler(message: Message) -> None:
    await get_mine_resources(message, 1)


async def get_mine_resources(message: Message, page: int, call: Optional[CallbackQuery] = None) -> None:
    """Выводит список записанных на пользователя ресурсов на определенной странице"""
    user = await Visitor.get_current(message.chat.id)
    resources = await Resource.get_resources_on_user(user)
    if len(resources) == 0:
        await message.answer(strings.user_have_no_device_msg)  # type: ignore
        return
    paginator = tg.Paginator(page, resources)
    keyboard = paginator.create_keyboard("mine")
    notes = await dbhelper.format_notes(paginator.get_objects_on_page(), message.chat.id)
    text = paginator.result_message() + notes
    if not call:
        await message.answer(text=text, reply_markup=keyboard)  # type: ignore
    else:
        await call.message.edit_text(text=text, reply_markup=keyboard)  # type: ignore


@router.callback_query(F.data.startswith("mine"))
async def mine_callback_handler(call: CallbackQuery) -> None:
    await call.answer()
    data = str(call.data)
    page_number = int(data.split()[1])
    await get_mine_resources(call.message, page_number, call)  # type: ignore


@router.message(Command("categories"))
async def get_categories_handler(message: Message) -> None:
    active_categories = await Resource.get_categories()
    if len(active_categories) == 0:
        await message.answer("Не найдена ни одна категория")
        return
    await message.answer(
        text=strings.ask_category_msg,
        reply_markup=tg.get_inline_keyboard(active_categories, "categories")
    )


@router.callback_query(F.data.startswith("categories"))
async def category_callback_handler(call: CallbackQuery):
    await call.answer()
    data = str(call.data).split()
    if len(data) <= 2:
        page = 1
        category = str(call.data).split()[1]
    else:
        page = int(data[1])
        category = data[2]
    resources = await Resource.get({"category_name": category})
    if len(resources) == 0:
        await call.message.answer(strings.not_found_msg)  # type: ignore
        return
    paginator = tg.Paginator(page, resources)
    keyboard = paginator.create_keyboard("categories", category)
    notes = await dbhelper.format_notes(paginator.get_objects_on_page(), call.message.chat.id)
    text = paginator.result_message() + notes
    await call.message.edit_text(text=text, reply_markup=keyboard)  # type: ignore


@router.message(F.text)
async def search_resource_handler(message: Message) -> None:
    text = message.text.strip()
    if text is None or text == "":
        await welcome_handler(message)
        return
    await search_resource(message, 1, False)
