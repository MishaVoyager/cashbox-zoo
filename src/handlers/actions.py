"""
Роутер для дополнительных действий с ресурсом: вернуть, встать в очередь, покинуть очередь
"""

import logging
from re import Match

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardRemove

from database import dbhelper
from database.models import Resource, Visitor, Record, ActionType
from handlers import strings
from helpers.fsmhelper import Buttons, CHOOSE_CONFIRM_OR_CANCEL_MSG, CONFIRM_OR_CANCEL_KEYBOARD

router = Router()


class ActionsFSM(StatesGroup):
    confirm = State()


@router.message(F.text.regexp(r"^(\/return|\/queue|\/leave)(\d+)$").as_("match"))
async def actions_handler(message: Message, match: Match[str], state: FSMContext) -> None:
    action = match.group(1)
    resource_id = int(match.group(2))
    await message.answer(
        text="Вы уверены?",
        reply_markup=CONFIRM_OR_CANCEL_KEYBOARD)
    await state.set_state(ActionsFSM.confirm)
    await state.set_data({"action": action, "resource_id": resource_id})


@router.message(ActionsFSM.confirm)
async def confirm_handler(message: Message, state: FSMContext) -> None:
    if message.text.strip() != Buttons.CONFIRM:
        await message.answer(CHOOSE_CONFIRM_OR_CANCEL_MSG)
        return
    data = await state.get_data()
    resource_id = data["resource_id"]
    action = data["action"]
    reply = ""
    match action:
        case "/return":
            reply = await return_resource(message, resource_id)
        case "/queue":
            reply = await queue_resource(message, resource_id)
        case "/leave":
            reply = await leave_resource(message, resource_id)
    await message.answer(text=reply, reply_markup=ReplyKeyboardRemove())
    await state.clear()


async def return_resource(message: Message, resource_id: int) -> str:
    """Списывает ресурс с пользователя и уведомляет его об этом"""
    resources = await Resource.get_by_primary(resource_id)
    username = strings.get_username_str(message)
    if len(resources) == 0:
        logging.error(
            f"Пользователь{username}с chat_id{message.chat.id} пытался вернуть "
            f"ресурс с resource_id {resource_id}, но оно не нашлось")
        return strings.unexpected_resource_not_found_error_msg
    resource: Resource = resources[0]
    user = await Visitor.get_current(message.chat.id)
    if resource.user_email != user.email:
        logging.error(f"Пользователь {repr(user)} пытался вернуть ресурс, "
                      f"записанное на другого пользователя: {repr(resource)}")
        return strings.return_others_device_msg
    await dbhelper.return_resource(resource_id)
    next_user_email = await dbhelper.pass_resource_to_next_user(resource_id)
    if next_user_email:
        await dbhelper.notify_next_user_about_take(message, next_user_email, resource)
    logging.info(f"Пользователь {repr(user)} вернул ресурс {repr(resource)}")
    return f"Списали с вас {resource.short_str()}"


async def queue_resource(message: Message, resource_id: int) -> str:
    """Записывает пользователя в очередь на ресурс и возвращает текст ответа"""
    resource = (await Resource.get_by_primary(resource_id))[0]
    user = await Visitor.get_current(message.chat.id)
    records = await dbhelper.get_resource_queue(resource_id)
    if user.email in [record.user_email for record in records]:
        return strings.queue_second_time_error_msg
    await Record.add(resource_id=resource.id, email=user.email, action=ActionType.QUEUE)
    logging.info(f"Пользователь {repr(user)} встал в очередь на ресурс {repr(resource)}")
    return f"Добавили вас в очередь на {resource.short_str()}"


async def leave_resource(message: Message, resource_id: int) -> str:
    """Выписывает пользователя из очереди на ресурс и возвращает текст ответа"""
    resource = (await Resource.get_by_primary(resource_id))[0]
    user = await Visitor.get_current(message.chat.id)
    records = await dbhelper.get_resource_queue(resource_id)
    if user.email not in [record.user_email for record in records]:
        logging.info(f"Пользователь {repr(user)} пытался дважды покинуть очередь на ресурс {repr(resource)}")
        return strings.leave_left_error_msg
    result = await Record.delete(**{
        dbhelper.nameof(Record.resource): resource_id,
        dbhelper.nameof(Record.action): ActionType.QUEUE,
        dbhelper.nameof(Record.user_email): user.email})
    if result:
        logging.info(f"Пользователь {repr(user)} покинул очередь на ресурс {repr(resource)}")
        return "Вы покинули очередь за устройством"
    else:
        logging.error(f"Пользователь {repr(user)} не смог покинуть очередь "
                      f"на ресурс {repr(resource)} из-за ошибки удаления Record")
        return strings.leaving_queue_error_msg
