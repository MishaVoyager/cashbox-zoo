"""
Роутер для админской возможности - отредактировать ресурс.
Отредактировать можно конкретные поля, либо выполнить комплексные сценарии:
1. Списать ресурс с пользователя
2. Записать ресурс на пользователя
"""

import logging

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardRemove

import handlers.strings
from database import dbhelper, resource_checker
from database.models import Record, Resource
from handlers import strings
from helpers import fsmhelper, tghelper as tg
from helpers.fsmhelper import Buttons, CHOOSE_CONFIRM_OR_RETURN_MSG, CONFIRM_OR_RETURN_KEYBOARD, \
    SKIP_OR_RETURN_KEYBOARD, fill_date


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


class EditButtons:
    DATE = "Дата регистрации"
    FIRMWARE = "Прошивка"
    COMMENT = "Комментарий"
    GIVE_TO = "Записать на пользователя"
    DELETE = "Удалить"
    TAKE_FROM = "Списать с пользователя"
    FINISH = "Завершить редактирование"
    CLEAR = "Очистить поле"


CLEAR_FIELD_KEYBOARD = tg.get_reply_keyboard([EditButtons.CLEAR])


def buttons_for_edit(resource_is_free: bool) -> list[str]:
    """Возвращает кнопки в зависимости от того, свободен ли ресурс"""
    buttons = [EditButtons.DATE, EditButtons.FIRMWARE, EditButtons.COMMENT]
    if resource_is_free:
        buttons += [EditButtons.GIVE_TO, EditButtons.DELETE]
    else:
        buttons += [EditButtons.TAKE_FROM]
    buttons += [EditButtons.FINISH]
    return buttons


async def escape_editing(message: Message, state: FSMContext) -> None:
    """Выходит из режима редактирования"""
    data = await state.get_data()
    note = ""
    if "resource_id" in data.keys():
        resource_id = data["resource_id"]
        resource = await Resource.get_single(resource_id)
        note = await dbhelper.format_note(resource, message.chat.id)
    await state.clear()
    await message.answer(
        text=f"Вы завершили редактирование\r\n\r\n{note}",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(StateFilter(EditFSM), F.text.lower().startswith(EditButtons.FINISH.lower()))
async def stop_editing_handler(message: Message, state: FSMContext) -> None:
    await escape_editing(message, state)


@router.message(StateFilter(EditFSM), F.text.lower().startswith(Buttons.RETURN.lower()))
async def cancel_handler(message: Message, state: FSMContext) -> None:
    resource_id = (await state.get_data())["resource_id"]
    resource = await Resource.get_single(resource_id)
    await state.set_state(EditFSM.choosing)
    note = await dbhelper.format_note(resource, message.chat.id)
    await message.answer(
        text=f"Вы вернулись к редактированию\r\n\r\n{note}",
        reply_markup=tg.get_reply_keyboard(buttons_for_edit(not resource.user_email))
    )


@router.message(F.text.regexp(r"\/edit.+"))
async def edit_resource_handler(message: Message, state: FSMContext) -> None:
    if not await resource_checker.is_admin(message.chat.id):
        await message.answer(strings.not_admin_error_msg)
        return
    resource_id = int(message.text.removeprefix("/edit"))
    resource = await Resource.get_single(resource_id)
    buttons = buttons_for_edit(not resource.user_email)
    await state.set_state(EditFSM.choosing)
    await state.update_data(resource_id=resource_id)
    await message.answer(
        text="Выберите действие",
        reply_markup=tg.get_reply_keyboard(buttons)
    )


@router.message(EditFSM.choosing)
async def choosing_handler(message: Message, state: FSMContext) -> None:
    match message.text:
        case EditButtons.COMMENT:
            field_name = dbhelper.nameof(Resource.comment)
        case EditButtons.DATE:
            field_name = dbhelper.nameof(Resource.reg_date)
        case EditButtons.FIRMWARE:
            field_name = dbhelper.nameof(Resource.firmware)
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
            await escape_editing(message, state)
            return
    await state.update_data(field_name=field_name)
    await state.set_state(EditFSM.editing)
    await message.answer(
        text="Введите значение",
        reply_markup=CLEAR_FIELD_KEYBOARD
    )


@router.message(EditFSM.editing)
async def editing_handler(message: Message, state: FSMContext) -> None:
    value = message.text.strip().lower()
    field_name = (await state.get_data())["field_name"]
    if value == EditButtons.CLEAR.lower():
        value = None
    if field_name == dbhelper.nameof(Resource.reg_date) and value:
        value = resource_checker.try_convert_to_ddmmyyyy(value)
        if not value:
            await message.answer(handlers.strings.ResourceError.WRONG_DATE.value)
            return
    resource_id = (await state.get_data())["resource_id"]
    resource = await Resource.update(resource_id, **{field_name: value})
    logging.info(
        f"Пользователь{strings.get_username_str(message)}с chat_id {message.chat.id} отредактировал "
        f"поле {field_name} для ресурса {repr(resource)}")
    await state.set_state(EditFSM.choosing)
    await message.answer(
        text=strings.edit_success_msg,
        reply_markup=tg.get_reply_keyboard(buttons_for_edit(not resource.user_email))
    )


@router.message(EditFSM.confirm_free_resource)
async def confirm_free_handler(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    resource_id = (await state.get_data())["resource_id"]
    if text == Buttons.CONFIRM:
        resource = await Resource.get_single(resource_id)
        await dbhelper.return_resource(resource_id)
        logging.info(
            f"Админ{strings.get_username_str(message)}с chat_id {message.chat.id} списал "
            f"с пользователя ресурс {repr(resource)}")
        await dbhelper.notify_user_about_return(message, resource.user_email, resource)
        next_user_email = await dbhelper.pass_resource_to_next_user(resource_id)
        if next_user_email:
            await dbhelper.notify_next_user_about_take(message, next_user_email, resource)
        await state.set_state(EditFSM.choosing)
        await message.answer(
            text=strings.get_take_from_user_msg(resource.user_email, resource),
            reply_markup=tg.get_reply_keyboard(buttons_for_edit(True))
        )
    else:
        await message.answer(CHOOSE_CONFIRM_OR_RETURN_MSG)


@router.message(EditFSM.confirm_delete)
async def confirm_delete_handler(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    resource_id = (await state.get_data())["resource_id"]
    if text == Buttons.CONFIRM:
        resource: Resource = await Resource.get_single(resource_id)
        if resource.user_email:
            await message.answer(
                text=strings.delete_taken_error_msg,
                reply_markup=ReplyKeyboardRemove()
            )
            await state.clear()
            return
        await Resource.delete(resource_id)
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
        await message.answer(handlers.strings.ResourceError.WRONG_EMAIL.value)
        return
    await state.update_data({dbhelper.nameof(Resource.user_email): user_email})
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
    await state.update_data({dbhelper.nameof(Resource.address): address})
    await state.set_state(EditFSM.choose_return_date)
    await message.answer(
        text=strings.ask_return_date_msg,
        reply_markup=SKIP_OR_RETURN_KEYBOARD
    )


@router.message(EditFSM.choose_return_date)
async def add_return_date(message: Message, state: FSMContext) -> None:
    await fill_date(
        message,
        state,
        EditFSM.confirm_take_resource,
        dbhelper.nameof(Resource.return_date),
        "Подтвердите запись устройства на пользователя",
        CONFIRM_OR_RETURN_KEYBOARD,
        True
    )


@router.message(EditFSM.confirm_take_resource)
async def finish_adding_resource(message: Message, state: FSMContext) -> None:
    command = message.text.strip()
    if command != Buttons.CONFIRM:
        await message.answer(CHOOSE_CONFIRM_OR_RETURN_MSG)
        return
    data = await state.get_data()
    resource: Resource = await Resource.take(
        resource_id=data["resource_id"],
        user_email=data["user_email"],
        address=data["address"],
        return_date=fsmhelper.restore_datetime(data["return_date"])
    )
    await Record.add(data["resource_id"], data["user_email"], dbhelper.ActionType.TAKE)
    await state.set_state(EditFSM.choosing)
    await message.answer(
        text=strings.get_pass_to_user_msg(resource),
        reply_markup=tg.get_reply_keyboard(buttons_for_edit(False))
    )
    await dbhelper.notify_user_about_take(message, data['user_email'], resource)
    logging.info(
        f"Админ{strings.get_username_str(message)}с chat_id {message.chat.id} записал "
        f"на пользователя ресурс: {repr(resource)}")
