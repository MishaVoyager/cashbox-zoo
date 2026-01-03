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

from helpers import tghelper as tg
from helpers.fsmhelper import Buttons, CHOOSE_CONFIRM_OR_RETURN_MSG, CONFIRM_OR_RETURN_KEYBOARD, RETURN_KEYBOARD
from helpers.texthelper import format_date
from helpers.tghelper import render_visitors, SEPARATOR_FOR_CALLBACK_DATA
from middlewares.authorize_middleware import Authorize
from resources import strings
from service import resource_checker
from service.services import VisitorService


class UsersFSM(StatesGroup):
    search = State()
    ask_comment = State()
    confirm_comment = State()
    ask_new_email = State()
    confirm_email = State()
    confirm_delete = State()


router = Router()
router.message.middleware(Authorize())
router.callback_query.middleware(Authorize())


@router.message(Command("users"))
async def users_handler(message: Message, state: FSMContext, visitor_service: VisitorService) -> None:
    await search_user(visitor_service, message, 1, True)
    await state.set_state(UsersFSM.search)
    await message.answer(
        "Включен режим поиска по пользователям. Воспользуйтесь списком выше или "
        "поищите по почте, имени, нику или id.\n\n"
        "/cancel - вернуться в режим поиска по устройствам"
    )


@router.message(StateFilter(UsersFSM), F.text.lower().startswith(Buttons.RETURN.lower()))
async def return_handler(message: Message, state: FSMContext) -> None:
    await return_to_search(
        message,
        state,
        "Вы вернулись к поиску по пользователям\n\n/cancel - вернуться в режим поиска по устройствам"
    )


async def return_to_search(message: Message, state: FSMContext, reply: str) -> None:
    """Возвращает в режим поиска по пользователям"""
    await state.clear()
    await state.set_state(UsersFSM.search)
    await message.answer(
        text=reply,
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(UsersFSM.confirm_delete)
async def confirm_delete_handler(
        message: Message,
        state: FSMContext,
        visitor_service: VisitorService
) -> None:
    if message.text != Buttons.CONFIRM:
        await message.answer(
            text=CHOOSE_CONFIRM_OR_RETURN_MSG,
            reply_markup=CONFIRM_OR_RETURN_KEYBOARD
        )
        return
    data = await state.get_data()
    get_result = await visitor_service.get_by_id(data["visitor_id"])
    visitor = get_result.unwrap()
    if not visitor:
        await return_to_search(message, state, strings.user_not_found_msg)
        logging.error(f"При удалении пользователя не найден пользователь с id {visitor.id}")
        return
    get_taken_result = await visitor_service.get_taken_resources(visitor)
    resources = get_taken_result.unwrap()
    if len(resources) != 0:
        await return_to_search(
            message,
            state,
            f"Нельзя удалить пользователя: сначала спишите с него устройства с id {', '.join([str(i.id) for i in resources])}"
        )
        logging.info(f"Не удалось удалить пользователя {repr(visitor)}: есть записанные ресурсы")
        return
    await visitor_service.delete(visitor.email)
    await return_to_search(message, state, f"Пользователь {visitor.email} успешно удален")
    logging.warning(f"Админ c chat_id {message.chat.id} удалил пользователя: {repr(visitor)}")


@router.message(UsersFSM.confirm_email)
async def confirm_email_handler(message: Message, state: FSMContext, visitor_service: VisitorService) -> None:
    if message.text != Buttons.CONFIRM:
        await message.answer(
            text=CHOOSE_CONFIRM_OR_RETURN_MSG,
            reply_markup=CONFIRM_OR_RETURN_KEYBOARD
        )
        return
    data = await state.get_data()
    visitor_id = data["visitor_id"]
    update_result = await visitor_service.update(visitor_id, data["new_email"])
    if update_result.is_failure:
        await return_to_search(message, state, strings.user_not_found_msg)
        logging.error(f"При обновлении email не найден пользователь с id {visitor_id}")
        return
    visitor = update_result.unwrap()
    await return_to_search(
        message,
        state,
        f"Почта обновлена. Результат: \r\n\r\n{render_visitors([visitor])}"
    )
    logging.info(f"Обновлена почта пользователя {repr(visitor)}")


@router.message(UsersFSM.ask_new_email)
async def ask_email_handler(message: Message, state: FSMContext, visitor_service: VisitorService) -> None:
    new_email = message.text.strip().lower()
    if resource_checker.is_kontur_email(new_email) is None:
        await message.answer(
            text=strings.ResourceError.WRONG_EMAIL.value,  # type: ignore
            reply_markup=RETURN_KEYBOARD
        )
        return
    get_result = await visitor_service.get(new_email)
    if get_result.is_failure:
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
async def confirm_comment_handler(message: Message, state: FSMContext, visitor_service: VisitorService) -> None:
    if message.text != Buttons.CONFIRM:
        await message.answer(
            text=CHOOSE_CONFIRM_OR_RETURN_MSG,
            reply_markup=CONFIRM_OR_RETURN_KEYBOARD
        )
        return
    data = await state.get_data()
    update_result = await visitor_service.update(data["visitor_id"], comment=data["comment"])
    if update_result.is_failure:
        await return_to_search(message, state, strings.user_not_found_msg)
        logging.error(f"Ошибка при обновлении коммента: не найден пользователь с id {data['visitor_id']}")
        return
    visitor = update_result.unwrap()
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


@router.message(StateFilter(UsersFSM),
                F.text.regexp(r"^(\/comment|\/email|\/delete|\/user_history)(\d+)$").as_("match"))
async def actions_handler(
        message: Message,
        match: Match[str],
        state: FSMContext,
        visitor_service: VisitorService
) -> None:
    action = match.group(1)
    visitor_id = int(match.group(2))
    await state.set_data({"visitor_id": visitor_id})
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
    elif action == "/user_history":
        get_finished_result = await visitor_service.get_finished_records(visitor_id)
        visitor_infos = get_finished_result.unwrap()
        if len(visitor_infos) == 0:
            await message.answer("Пока что нет данных об истории", reply_markup=ReplyKeyboardRemove())
            await state.clear()
            return
        reply = f"История для пользователя {visitor_infos[0].visitor_email} (@{visitor_infos[0].visitor_username}):\n\n"
        for i in visitor_infos:
            reply += f"{format_date(i.take_date)} - {format_date(i.return_date)}: {i.resource_name} с id {i.resource_id}. Адрес: {i.address or 'не указан'}\n"
        await message.answer(reply, reply_markup=ReplyKeyboardRemove())
        await state.clear()
    else:
        await message.answer("Выбрано некорректное действие над пользователем")


@router.callback_query(F.data.startswith("search_user"))
async def search_callback(call: CallbackQuery, visitor_service: VisitorService) -> None:
    await call.answer()
    data = (str(call.data)).split(SEPARATOR_FOR_CALLBACK_DATA)
    page_number = int(data[1])
    search_users_by_query = len(data) >= 2
    if search_users_by_query:
        query = " ".join(data[2:])
        search_result = await visitor_service.search(query)
        visitors = search_result.unwrap()
    else:
        query = ''
        visitors = (await visitor_service.get_all()).unwrap()
    paginator = tg.Paginator(page_number, visitors)
    reply = paginator.result_message() + render_visitors(paginator.get_objects_on_page())
    await call.message.edit_text(  # type: ignore
        text=reply,
        reply_markup=paginator.create_keyboard("search_user", query)
    )


async def search_user(visitor_service: VisitorService, message: Message, page_number: int,
                      get_all: bool = False) -> None:
    """Выводит список пользователей на определенной странице"""
    query = '' if get_all else message.text.replace("@", "")
    if get_all:
        visitors = (await visitor_service.get_all()).unwrap()
    else:
        visitors = (await visitor_service.search(query)).unwrap()
    if len(visitors) == 0:
        reply = "Пользователь не найден. Поищите иначе или вернитесь в режим поиска по устройствам: /cancel"
        await message.answer(reply)
        return
    paginator = tg.Paginator(page_number, visitors)
    reply = paginator.result_message() + render_visitors(paginator.get_objects_on_page())
    await message.answer(
        text=reply,
        reply_markup=paginator.create_keyboard("search_user", query)
    )


@router.message(StateFilter(UsersFSM), F.text)
async def search_user_handler(message: Message, visitor_service: VisitorService) -> None:
    await search_user(visitor_service, message, 1, False)
