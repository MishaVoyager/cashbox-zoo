"""
Роутер для дополнительных действий с ресурсом: вернуть, встать в очередь, покинуть очередь
"""

import logging
from re import Match

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardRemove

from domain.models import Visitor, ActionType
from domain.resource_info import ResourceInfoDTO
from helpers.fsmhelper import Buttons, CHOOSE_CONFIRM_OR_CANCEL_MSG, CONFIRM_OR_CANCEL_KEYBOARD
from resources import strings
from service.services import ResourceService, RecordService
from service.notification_service import NotificationService

router = Router()


class ActionsFSM(StatesGroup):
    confirm = State()


@router.message(F.text.regexp(r"^(\/return|\/queue|\/leave)(\d+)$").as_("match"))
async def actions_handler(message: Message, match: Match[str], state: FSMContext) -> None:
    action = match.group(1)
    resource_id = int(match.group(2))
    await state.set_data({"action": action, "resource_id": resource_id})
    await message.answer(
        text="Вы уверены?",
        reply_markup=CONFIRM_OR_CANCEL_KEYBOARD)
    await state.set_state(ActionsFSM.confirm)


@router.message(ActionsFSM.confirm)
async def confirm_handler(
        message: Message,
        state: FSMContext,
        visitor: Visitor,
        resource_service: ResourceService,
        record_service: RecordService,
        notification_service: NotificationService
) -> None:
    if message.text.strip() != Buttons.CONFIRM:
        await message.answer(CHOOSE_CONFIRM_OR_CANCEL_MSG)
        return
    data = await state.get_data()
    resource_id = data["resource_id"]
    service_result = await resource_service.get(resource_id)
    resource = service_result.unwrap()
    action = data["action"]
    reply = ""
    match action:
        case "/return":
            reply = await return_resource(resource, visitor, record_service, notification_service)
        case "/queue":
            reply = await queue_resource(resource, visitor, record_service)
        case "/leave":
            reply = await leave_resource(resource, visitor, record_service)
    await message.answer(text=reply, reply_markup=ReplyKeyboardRemove())
    await state.clear()


async def return_resource(
        resource: ResourceInfoDTO,
        visitor: Visitor,
        record_service: RecordService,
        notification_service: NotificationService
) -> str:
    """Списывает ресурс с пользователя и уведомляет его об этом"""
    get_action_result = await record_service.get_available_action(resource.id, visitor.email)
    action = get_action_result.unwrap()
    if action != ActionType.RETURN:
        return strings.return_others_device_msg
    return_resource_result = await record_service.return_resource(resource.id)
    if return_resource_result.is_failure:
        return strings.return_others_device_msg
    resource_dto = return_resource_result.unwrap()
    logging.info(f"{repr(visitor)} вернул {repr(resource_dto.resource)}")
    if resource_dto.new_visitor_email:
        await notification_service.notify_next_user_about_take(resource_dto.new_visitor_email, resource_dto.resource)
    return strings.confirm_return_msg(resource)


async def queue_resource(resource: ResourceInfoDTO, visitor: Visitor, record_service: RecordService) -> str:
    """Записывает пользователя в очередь на ресурс и возвращает текст ответа"""
    result = await record_service.enqueue(resource.id, visitor.email)
    if result.is_failure:
        logging.info(f"{repr(visitor)} не смог встать в очередь на {repr(resource)}")
        return strings.queue_second_time_error_msg
    logging.info(f"{repr(visitor)} встал в очередь на ресурс {repr(resource)}")
    return strings.confirm_queue_msg(resource)


async def leave_resource(resource: ResourceInfoDTO, visitor: Visitor, record_service: RecordService) -> str:
    """Выписывает пользователя из очереди на ресурс и возвращает текст ответа"""
    result = await record_service.leave_queue(resource.id, visitor.email)
    if result.is_failure:
        logging.info(f"{repr(visitor)} не смог покинуть очередь на {repr(resource)}")
        return strings.leaving_queue_error_msg
    logging.info(f"Пользователь {repr(visitor)} покинул очередь на ресурс {repr(resource)}")
    return strings.confirm_leave_msg(resource)
