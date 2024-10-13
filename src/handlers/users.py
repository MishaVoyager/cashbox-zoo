"""
Роутер для админа, который позволяет получать инфу про пользователей.
А также можно менять почту пользователей, оставлять комментарии и удалять.
"""

import logging
from re import Match

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

import handlers.strings
from database import resource_checker
from database.models import Resource, Visitor
from handlers import strings
from helpers import tghelper as tg
from helpers.fsmhelper import Buttons, CHOOSE_CONFIRM_OR_RETURN_MSG, CONFIRM_OR_RETURN_KEYBOARD, RETURN_KEYBOARD
from helpers.tghelper import render_visitors


class UsersFSM(StatesGroup):
    search = State()
    ask_comment = State()
    confirm_comment = State()
    ask_new_email = State()
    confirm_email = State()
    confirm_delete = State()


class UserButtons:
    OUT = "Выйти"
    EVERYONE = "Все пользователи"


ASK_KEYBOARD = tg.get_reply_keyboard([UserButtons.EVERYONE, UserButtons.OUT])

router = Router()


@router.message(StateFilter(UsersFSM), F.text.lower().startswith(UserButtons.OUT.lower()))
async def cancel_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        text="Вы вышли из режима поиска по пользователям",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(StateFilter(UsersFSM), F.text.lower().startswith(Buttons.RETURN.lower()))
async def return_handler(message: Message, state: FSMContext) -> None:
    await return_to_search(message, state, "Вы вернулись к поиску по пользователям")


async def return_to_search(message: Message, state: FSMContext, reply: str) -> None:
    """Возвращает в меню поиска по пользователям"""
    await state.clear()
    await state.set_state(UsersFSM.search)
    await message.answer(
        text=reply,
        reply_markup=ASK_KEYBOARD
    )


@router.message(UsersFSM.confirm_delete)
async def confirm_delete_handler(message: Message, state: FSMContext) -> None:
    if message.text != Buttons.CONFIRM:
        await message.answer(
            text=CHOOSE_CONFIRM_OR_RETURN_MSG,
            reply_markup=CONFIRM_OR_RETURN_KEYBOARD
        )
        return
    data = await state.get_data()
    visitor_id = data["visitor_id"]
    visitors: list[Visitor] = await Visitor.get({"id": visitor_id})
    if len(visitors) == 0:
        await return_to_search(message, state, strings.user_not_found_msg)
        logging.error(f"При удалении пользователя не найден пользователь с id {visitor_id}")
        return
    resources = await Resource.get({"user_email": visitors[0].email})
    if len(resources) != 0:
        await return_to_search(message, state, "Нельзя удалить пользователя: сначала спишите с него устройства")
        logging.info(f"Не удалось удалить пользователя {repr(visitors[0])}: есть записанные ресурсы")
        return
    await Visitor.delete_existed(visitors[0])
    await return_to_search(message, state, f"Пользователь {visitors[0].email} успешно удален")
    logging.warning(f"Админ c chat_id {message.chat.id} удалил пользователя: {repr(visitors[0])}")


@router.message(UsersFSM.confirm_email)
async def confirm_email_handler(message: Message, state: FSMContext) -> None:
    if message.text != Buttons.CONFIRM:
        await message.answer(
            text=CHOOSE_CONFIRM_OR_RETURN_MSG,
            reply_markup=CONFIRM_OR_RETURN_KEYBOARD
        )
        return
    data = await state.get_data()
    visitor_id = data["visitor_id"]
    visitor = await Visitor.update_email(visitor_id, data["new_email"])
    if not visitor:
        await return_to_search(message, state, strings.user_not_found_msg)
        logging.error(f"При обновлении email не найден пользователь с id {visitor_id}")
        return
    await return_to_search(
        message,
        state,
        f"Почта обновлена. Результат: \r\n\r\n{render_visitors([visitor])}"
    )
    logging.info(f"Обновлена почта пользователя {repr(visitor)}")


@router.message(UsersFSM.ask_new_email)
async def ask_email_handler(message: Message, state: FSMContext) -> None:
    new_email = message.text.strip().lower()
    if resource_checker.is_kontur_email(new_email) is None:
        await message.answer(
            text=handlers.strings.ResourceError.WRONG_EMAIL.value,  # type: ignore
            reply_markup=RETURN_KEYBOARD
        )
        return
    visitors = await Visitor.get_by_email(new_email)
    if len(visitors) != 0:
        await message.answer(
            text="Пользователь с такой почтой уже есть. Укажите другую почту",
            reply_markup=RETURN_KEYBOARD
        )
        return
    await state.update_data(new_email=new_email)
    await state.set_state(UsersFSM.confirm_email)
    await message.answer(
        text="Точно-точно обновляем почту пользователя?",
        reply_markup=CONFIRM_OR_RETURN_KEYBOARD
    )


@router.message(UsersFSM.confirm_comment)
async def confirm_comment_handler(message: Message, state: FSMContext) -> None:
    if message.text != Buttons.CONFIRM:
        await message.answer(
            text=CHOOSE_CONFIRM_OR_RETURN_MSG,
            reply_markup=CONFIRM_OR_RETURN_KEYBOARD
        )
        return
    data = await state.get_data()
    visitor = await Visitor.update_comment(data["visitor_id"], data["comment"])
    if not visitor:
        await return_to_search(message, state, strings.user_not_found_msg)
        logging.error(f"Ошибка при обновлении коммента: не найден пользователь с id {data['visitor_id']}")
        return
    await return_to_search(
        message,
        state,
        f"Комментарий обновлен. Результат: \r\n\r\n{render_visitors([visitor])}"
    )
    logging.info(f"Обновлен комментарий пользователя {repr(visitor)}")


@router.message(UsersFSM.ask_comment)
async def ask_comment_handler(message: Message, state: FSMContext) -> None:
    await state.update_data({"comment": message.text})
    await state.set_state(UsersFSM.confirm_comment)
    await message.answer(
        text="Точно заменяем комментарий на новый?",
        reply_markup=CONFIRM_OR_RETURN_KEYBOARD
    )


@router.message(StateFilter(UsersFSM), F.text.regexp(r"^(\/comment|\/email|\/delete)(\d+)$").as_("match"))
async def actions_handler(message: Message, match: Match[str], state: FSMContext) -> None:
    visitor = await Visitor.get_current(message.chat.id)
    if not visitor.is_admin:
        await message.answer(strings.not_found_msg)
        await state.clear()
        return
    action = match.group(1)
    await state.set_data({"visitor_id": int(match.group(2))})
    if action == "/comment":
        await state.set_state(UsersFSM.ask_comment)
        await message.answer(
            text="На какой комментарий вы хотите заменить текущий?",
            reply_markup=RETURN_KEYBOARD
        )
    elif action == "/email":
        await state.set_state(UsersFSM.ask_new_email)
        await message.answer(
            text="Введите новую почту в формате email@skbkontur.ru",
            reply_markup=RETURN_KEYBOARD
        )
    elif action == "/delete":
        await state.set_state(UsersFSM.confirm_delete)
        await message.answer(
            text="Вы уверены, что хотите удалить пользователя?",
            reply_markup=CONFIRM_OR_RETURN_KEYBOARD
        )
    else:
        await message.answer("Выбрано некорректное действие над пользователем")


@router.message(Command("users"))
async def users_handler(message: Message, state: FSMContext) -> None:
    user = await Visitor.get_current(message.chat.id)
    if not user.is_admin:
        await message.answer(strings.not_found_msg)
        return
    await state.set_state(UsersFSM.search)
    await message.answer(
        text="Введите данные пользователя или выберите Все пользователи",
        reply_markup=ASK_KEYBOARD
    )


@router.callback_query(F.data.startswith("search_user"))
async def search_callback(call: CallbackQuery) -> None:
    await call.answer()
    data = (str(call.data)).split()
    page_number = int(data[1])
    search_users_by_query = len(data) >= 2
    if search_users_by_query:
        query = " ".join(data[2:])
        visitors = await Visitor.search(query)
    else:
        query = ''
        visitors = await Visitor.get_all()
    paginator = tg.Paginator(page_number, visitors)
    reply = paginator.result_message() + render_visitors(paginator.get_objects_on_page())
    await call.message.edit_text(  # type: ignore
        text=reply,
        reply_markup=paginator.create_keyboard("search_user", query)
    )


@router.message(UsersFSM.search)
async def choosing_handler(message: Message) -> None:
    if message.text == "Все пользователи":
        await search_user(message, 1, True)
    else:
        await search_user(message, 1, False)


async def search_user(message: Message, page_number: int, get_all: bool = False) -> None:
    """Выводит список пользователей на определенной странице"""
    if get_all:
        query = ''
        visitors = await Visitor.get_all(100)
    else:
        query = message.text
        visitors = await Visitor.search(query)
    if len(visitors) == 0:
        await message.answer("Пользователь не найден, попробуйте поискать иначе")
        return
    paginator = tg.Paginator(page_number, visitors)
    reply = paginator.result_message() + render_visitors(paginator.get_objects_on_page())
    await message.answer(
        text=reply,
        reply_markup=paginator.create_keyboard("search_user", query)
    )
