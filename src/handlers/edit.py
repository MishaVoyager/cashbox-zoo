"""
Роутер для админской возможности - отредактировать ресурс.
Отредактировать можно конкретные поля, либо выполнить комплексные сценарии:
1. Списать ресурс с пользователя
2. Записать ресурс на пользователя
"""

import logging

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery
from aiogram_calendar import SimpleCalendarCallback

import resources.strings
from configs.config import Settings
from domain.models import Resource, Visitor, Record
from helpers import fsmhelper, tghelper as tg
from helpers.fsmhelper import Buttons, CHOOSE_CONFIRM_OR_RETURN_MSG, CONFIRM_OR_RETURN_KEYBOARD, \
    SKIP_OR_RETURN_KEYBOARD, fill_date_from_calendar, handle_text_instead_of_date_from_calendar
from helpers.presentation import format_note
from helpers.tghelper import start_calendar, nameof
from middlewares.authorize_middleware import Authorize
from resources import strings
from service import resource_checker
from service.notification_service import NotificationService
from service.resource_checker import try_convert_to_ddmmyyyy
from service.services import ResourceService, RecordService


class EditFSM(StatesGroup):
    choosing = State()
    editing = State()
    confirm_free_resource = State()
    confirm_delete = State()
    choose_email = State()
    choose_address = State()
    choose_return_date = State()
    choose_id = State()
    confirm_take_resource = State()


router = Router()
router.message.middleware(Authorize())
router.callback_query.middleware(Authorize())


class EditButtons:
    DATE = "Дата регистрации"
    FIRMWARE = "Прошивка"
    COMMENT = "Комментарий"
    CATEGORY = "Тип устройства"
    GIVE_TO = "Записать на пользователя"
    DELETE = "Удалить"
    TAKE_FROM = "Списать с пользователя"
    FINISH = "Завершить редактирование"
    CLEAR = "Очистить поле"


CLEAR_FIELD_KEYBOARD = tg.get_reply_keyboard([EditButtons.CLEAR])


def buttons_for_edit(resource_is_free: bool) -> list[str]:
    """Возвращает кнопки в зависимости от того, свободен ли ресурс"""
    buttons = [EditButtons.DATE, EditButtons.FIRMWARE, EditButtons.COMMENT, EditButtons.CATEGORY]
    if resource_is_free:
        buttons += [EditButtons.GIVE_TO, EditButtons.DELETE]
    else:
        buttons += [EditButtons.TAKE_FROM]
    buttons += [EditButtons.FINISH]
    return buttons


async def escape_editing(
        visitor: Visitor,
        message: Message,
        state: FSMContext,
        resource_service: ResourceService,
        record_service: RecordService
) -> None:
    """Выходит из режима редактирования"""
    data = await state.get_data()
    note = ""
    if "resource_id" in data.keys():
        resource_id = data["resource_id"]
        result = await resource_service.get(resource_id)
        resource = result.unwrap()
        action_result = await record_service.get_available_action(resource_id, visitor.email)
        action = action_result.unwrap()
        note = format_note(resource, visitor, action)
    await state.clear()
    await message.answer(
        text=f"Вы завершили редактирование\r\n\r\n{note}",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(StateFilter(EditFSM), F.text.lower().startswith(EditButtons.FINISH.lower()))
async def stop_editing_handler(
        message: Message,
        state: FSMContext,
        visitor: Visitor,
        resource_service: ResourceService,
        record_service: RecordService
) -> None:
    await escape_editing(visitor, message, state, resource_service, record_service)


@router.message(StateFilter(EditFSM), F.text.lower().startswith(Buttons.RETURN.lower()))
async def cancel_handler(
        message: Message,
        state: FSMContext,
        visitor: Visitor,
        resource_service: ResourceService,
        record_service: RecordService
) -> None:
    resource_id = (await state.get_data())["resource_id"]
    result = await resource_service.get(resource_id)
    resource = result.unwrap()
    action_result = await record_service.get_available_action(resource_id, visitor.email)
    action = action_result.unwrap()
    note = format_note(resource, visitor, action)
    get_take_result = await resource_service.get_take_record(resource_id)

    await message.answer(
        text=f"Вы вернулись к редактированию\r\n\r\n{note}",
        reply_markup=tg.get_reply_keyboard(buttons_for_edit(get_take_result.unwrap() is None))
    )


@router.message(F.text.regexp(r"\/edit.+"))
async def edit_resource_handler(message: Message, state: FSMContext, resource_service: ResourceService) -> None:
    resource_id = int(message.text.removeprefix("/edit"))
    get_take_result = await resource_service.get_take_record(resource_id)
    take_record = get_take_result.unwrap()
    buttons = buttons_for_edit(take_record is None)
    await state.set_state(EditFSM.choosing)
    await state.update_data(resource_id=resource_id)
    await message.answer(
        text="Выберите действие",
        reply_markup=tg.get_reply_keyboard(buttons)
    )


@router.message(EditFSM.choosing)
async def choosing_handler(
        message: Message,
        state: FSMContext,
        visitor: Visitor,
        resource_service: ResourceService,
        record_service: RecordService
) -> None:
    match message.text:
        case EditButtons.COMMENT:
            field_name = nameof(Resource.comment)
        case EditButtons.DATE:
            field_name = nameof(Resource.reg_date)
        case EditButtons.FIRMWARE:
            field_name = nameof(Resource.firmware)
        case EditButtons.CATEGORY:
            field_name = nameof(Resource.category_name)
            await state.update_data(field_name=field_name)
            await state.set_state(EditFSM.editing)
            await message.answer(
                text=strings.ask_category_msg,
                reply_markup=tg.get_reply_keyboard(Settings().get_categories())
            )
            return
        case EditButtons.TAKE_FROM:
            await state.set_state(EditFSM.confirm_free_resource)
            await message.answer(
                text="Точно хотите списать устройство с пользователя?",
                reply_markup=CONFIRM_OR_RETURN_KEYBOARD
            )
            return
        case EditButtons.DELETE:
            await state.set_state(EditFSM.confirm_delete)
            await message.answer(
                text="Точно хотите удалить устройство?",
                reply_markup=CONFIRM_OR_RETURN_KEYBOARD
            )
            return
        case EditButtons.GIVE_TO:
            await state.set_state(EditFSM.choose_email)
            await message.answer(
                text=strings.ask_email_msg,
                reply_markup=ReplyKeyboardRemove()
            )
            return
        case _:
            await escape_editing(visitor, message, state, resource_service, record_service)
            return
    await state.update_data(field_name=field_name)
    await state.set_state(EditFSM.editing)
    await message.answer(
        text="Введите значение",
        reply_markup=CLEAR_FIELD_KEYBOARD
    )


@router.message(EditFSM.editing)
async def editing_handler(message: Message, state: FSMContext, resource_service: ResourceService) -> None:
    value = message.text.strip()
    if value == EditButtons.CLEAR:
        value = None
    field_name = (await state.get_data())["field_name"]
    if field_name == nameof(Resource.reg_date) and value:
        value = try_convert_to_ddmmyyyy(value)
        if not value:
            await message.answer(resources.strings.ResourceError.WRONG_DATE.value)
            return
    if field_name == nameof(Resource.category_name) and value not in Settings().get_categories():
        await message.answer(f"{strings.ResourceError.WRONG_CATEGORY.value}. {strings.choose_option_msg}")
        return
    resource_id = (await state.get_data())["resource_id"]
    result = await resource_service.update_field(resource_id, field_name, value)
    resource = result.unwrap()
    get_take_result = await resource_service.get_take_record(resource_id)
    take_record = get_take_result.unwrap()
    logging.info(
        f"Пользователь{strings.get_username_str(message)}с chat_id {message.chat.id} отредактировал "
        f"поле {field_name} для ресурса {repr(resource)}")
    await state.set_state(EditFSM.choosing)
    await message.answer(
        text=strings.edit_success_msg,
        reply_markup=tg.get_reply_keyboard(buttons_for_edit(take_record is None))
    )


@router.message(EditFSM.confirm_free_resource)
async def confirm_free_handler(
        message: Message,
        state: FSMContext,
        record_service: RecordService,
        notification_service: NotificationService
) -> None:
    text = message.text.strip()
    resource_id = (await state.get_data())["resource_id"]
    if text == Buttons.CONFIRM:
        result = await record_service.return_resource(resource_id)
        return_resource_dto = result.unwrap()
        logging.info(
            f"Админ{strings.get_username_str(message)}с chat_id {message.chat.id} списал "
            f"с пользователя ресурс {repr(return_resource_dto.resource)}")
        await notification_service.notify_user_about_return(
            return_resource_dto.previous_visitor_email,
            return_resource_dto.resource
        )
        if return_resource_dto.new_visitor_email:
            await notification_service.notify_next_user_about_take(
                return_resource_dto.new_visitor_email,
                return_resource_dto.resource
            )
        await state.set_state(EditFSM.choosing)
        await message.answer(
            text=strings.get_take_from_user_msg(return_resource_dto.previous_visitor_email,
                                                return_resource_dto.resource),
            reply_markup=tg.get_reply_keyboard(buttons_for_edit(True))
        )
    else:
        await message.answer(CHOOSE_CONFIRM_OR_RETURN_MSG)


@router.message(EditFSM.confirm_delete)
async def confirm_delete_handler(message: Message, state: FSMContext, resource_service: ResourceService) -> None:
    text = message.text.strip()
    resource_id = (await state.get_data())["resource_id"]
    if text == Buttons.CONFIRM:
        result = await resource_service.get(resource_id)
        resource = result.unwrap()
        get_take_result = await resource_service.get_take_record(resource_id)
        # TODO перенести логику в сервис
        take_record = get_take_result.unwrap()
        if take_record and take_record.user_email:
            await message.answer(
                text=strings.delete_taken_error_msg,
                reply_markup=ReplyKeyboardRemove()
            )
            await state.clear()
            return
        delete_result = await resource_service.delete(resource_id)
        logging.info(
            f"Админ{strings.get_username_str(message)}с chat_id {message.chat.id} удалил "
            f"ресурс {repr(resource)}")
        await state.clear()
        await message.answer(
            text=strings.delete_success_msg,
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await message.answer(CHOOSE_CONFIRM_OR_RETURN_MSG)


@router.message(EditFSM.choose_email)
async def choose_email_handler(message: Message, state: FSMContext) -> None:
    user_email = message.text.strip()
    if not resource_checker.is_kontur_email(user_email):
        await message.answer(resources.strings.ResourceError.WRONG_EMAIL.value)
        return
    await state.update_data({nameof(Record.user_email): user_email})
    await state.set_state(EditFSM.choose_address)
    await message.answer(
        text=strings.ask_address_msg,
        reply_markup=SKIP_OR_RETURN_KEYBOARD
    )


@router.message(EditFSM.choose_address)
async def add_address(message: Message, state: FSMContext) -> None:
    address = message.text.strip()
    if Buttons.SKIP in address:
        address = None
    await state.update_data({nameof(Record.address): address})
    await state.set_state(EditFSM.choose_return_date)
    await message.answer(
        text=strings.ask_return_date_from_calendar_msg,
        reply_markup=await start_calendar()
    )


@router.callback_query(SimpleCalendarCallback.filter(), StateFilter(EditFSM.choose_return_date))
async def add_return_date(call: CallbackQuery, callback_data: CallbackData, state: FSMContext) -> None:
    await fill_date_from_calendar(
        call,
        callback_data,
        state,
        EditFSM.confirm_take_resource,
        nameof(Record.return_date),
        "Подтвердите запись устройства на пользователя",
        CONFIRM_OR_RETURN_KEYBOARD,
        True
    )


@router.message(EditFSM.choose_return_date)
async def message_instead_of_date_handler(message: Message, state: FSMContext) -> None:
    await handle_text_instead_of_date_from_calendar(
        message,
        state,
        EditFSM.confirm_take_resource,
        nameof(Record.return_date),
        "Подтвердите запись устройства на пользователя",
        CONFIRM_OR_RETURN_KEYBOARD
    )


@router.message(EditFSM.confirm_take_resource)
async def finish_adding_resource(
        message: Message,
        state: FSMContext,
        record_service: RecordService,
        notification_service: NotificationService
) -> None:
    command = message.text.strip()
    if command != Buttons.CONFIRM:
        await message.answer(CHOOSE_CONFIRM_OR_RETURN_MSG)
        return
    data = await state.get_data()
    take_result = await record_service.take_resource(
        data["resource_id"],
        data["user_email"],
        data["address"],
        fsmhelper.restore_datetime(data["return_date"])
    )
    resource_info = take_result.unwrap()
    await state.set_state(EditFSM.choosing)
    await message.answer(
        text=f"Вы записали {resource_info.short_str()} на пользователя {data['user_email']}",
        reply_markup=tg.get_reply_keyboard(buttons_for_edit(False))
    )
    await notification_service.notify_user_about_take(resource_info.user_email, resource_info)
    logging.info(
        f"Админ{strings.get_username_str(message)}с chat_id {message.chat.id} записал "
        f"на пользователя ресурс: {resource_info.values()}")
