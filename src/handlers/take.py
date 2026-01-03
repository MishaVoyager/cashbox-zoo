"""
Роутер, который позволяет пользователям записывать ресурс на себя.
"""

import logging

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery
from aiogram_calendar import SimpleCalendarCallback

from domain.models import Visitor, Record
from helpers import fsmhelper
from helpers.fsmhelper import Buttons, CHOOSE_CONFIRM_OR_CANCEL_MSG, CONFIRM_OR_CANCEL_KEYBOARD, fill_date_from_calendar
from helpers.tghelper import start_calendar, nameof
from resources import strings
from service.services import RecordService, ResourceService
from service.notification_service import NotificationService


class TakeFSM(StatesGroup):
    choosing_address = State()
    choosing_return_date = State()
    confirming = State()


router = Router()


@router.message(F.text.regexp(r"\/change.+"))
async def update_address_handler(message: Message, state: FSMContext, resource_service: ResourceService) -> None:
    resource_id = int(message.text.removeprefix("/change"))
    result = await resource_service.get_take_record(resource_id)
    if result.is_failure or not result.unwrap():
        await message.answer(strings.update_address_others_resource_msg)
        return
    record = result.unwrap()
    await message.answer(strings.ask_address_msg)
    await state.update_data(resource_id=resource_id, record_id=record.id)
    await state.set_state(TakeFSM.choosing_address)


@router.message(F.text.regexp(r"\/take.+"))
async def take_resource_handler(
        message: Message,
        state: FSMContext,
        resource_service: ResourceService
) -> None:
    resource_id = int(message.text.removeprefix("/take"))
    result = await resource_service.get(resource_id)
    if result.is_failure or not result.unwrap():
        await message.answer(strings.take_nonnexisted_error_msg)
        return
    await message.answer(strings.ask_address_msg)
    await state.update_data(resource_id=resource_id)
    await state.set_state(TakeFSM.choosing_address)


@router.message(TakeFSM.choosing_address)
async def enter_address(message: Message, state: FSMContext) -> None:
    address = message.text.lower().strip()
    await state.update_data(address=address)
    await state.set_state(TakeFSM.choosing_return_date)
    await message.answer(
        text=strings.ask_return_date_from_calendar_msg,
        reply_markup=await start_calendar()
    )


@router.callback_query(SimpleCalendarCallback.filter(), StateFilter(TakeFSM.choosing_return_date))
async def enter_return_date(call: CallbackQuery, callback_data: CallbackData, state: FSMContext) -> None:
    await fill_date_from_calendar(
        call,
        callback_data,
        state,
        TakeFSM.confirming,
        nameof(Record.return_date),
        "Подтвердите запись устройства на пользователя",
        CONFIRM_OR_CANCEL_KEYBOARD,
        True
    )


@router.message(TakeFSM.choosing_return_date)
async def message_instead_of_date_handler(message: Message) -> None:
    await message.answer("Выберите дату в календаре")


@router.message(TakeFSM.confirming)
async def confirm_take(
        message: Message,
        state: FSMContext,
        visitor: Visitor,
        record_service: RecordService,
        notification_service: NotificationService
) -> None:
    if message.text.lower() == Buttons.CONFIRM.lower():
        data = await state.get_data()
        resource_id = data["resource_id"]
        address = data["address"]
        date = fsmhelper.restore_datetime(data["return_date"])
        if "record_id" in data.keys():
            # Изменение текущей записи
            result = await record_service.put(data["record_id"], address, date)
            if result.is_failure:
                await message.answer(strings.update_record_error_msg)
                await state.clear()
                return
            resource_info = result.unwrap()
            logging.info(f"Пользователь {repr(visitor)} изменил запись: {resource_info.values()}")
            await message.answer(
                text=strings.update_record_success_msg,
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            # Создание новой записи
            result = await record_service.take_resource(resource_id, visitor.email, address, date)
            if result.is_failure and result.error_code == 404:
                await message.answer(strings.take_nonnexisted_error_msg)
                await state.clear()
                return
            if result.is_failure and result.error_code == 409:
                await message.answer(
                    text=strings.take_taken_error_msg,
                    reply_markup=ReplyKeyboardRemove()
                )
                await state.clear()
                return
            resource_info = result.unwrap()
            logging.info(f"Пользователь {repr(visitor)} взял ресурс {resource_info.values()}")
            await message.answer(
                text=strings.confirm_take_msg(resource_info),
                reply_markup=ReplyKeyboardRemove()
            )
            # TODO: подумать, как организовать уведомления лучше
        await state.clear()
    elif message.text.lower() == Buttons.CANCEL.lower():
        await state.clear()
        await message.answer(
            text=strings.deny_take_msg,
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await message.answer(CHOOSE_CONFIRM_OR_CANCEL_MSG)
