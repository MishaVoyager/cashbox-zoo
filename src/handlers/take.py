"""
Роутер, который позволяет пользователям записывать ресурс на себя.
"""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardRemove

from database import dbhelper
from database.models import ActionType, Record, Resource, Visitor
from handlers import strings
from helpers import fsmhelper
from helpers.fsmhelper import Buttons, CHOOSE_CONFIRM_OR_CANCEL_MSG, CONFIRM_OR_CANCEL_KEYBOARD, SKIP_KEYBOARD


class TakeFSM(StatesGroup):
    choosing_address = State()
    choosing_return_date = State()
    confirming = State()


router = Router()


@router.message(F.text.regexp(r"\/update_address.+"))
async def update_address_handler(message: Message, state: FSMContext) -> None:
    resource_id = int(message.text.removeprefix("/update_address"))
    resource: Resource = await Resource.get_single(resource_id)
    visitor = await Visitor.get_current(message.chat.id)
    if resource.user_email != visitor.email:
        await message.answer(strings.update_address_others_resource_msg)
        return
    await message.answer("Напишите, где будет находится устройство? Например: Офис Екб, мой стол. Или: Питер, дома")
    await state.update_data(resource_id=resource_id)
    await state.set_state(TakeFSM.choosing_address)


@router.message(F.text.regexp(r"\/take.+"))
async def take_resource_handler(message: Message, state: FSMContext) -> None:
    resource_id = int(message.text.removeprefix("/take"))
    await take_resource(message, state, resource_id)


async def take_resource(message: Message, state: FSMContext, resource_id: int) -> None:
    """Записывает ресурс на пользователя и уведомляет пользователя"""
    resource: Resource = await Resource.get_single(resource_id)
    if not resource:
        await message.answer(strings.take_nonnexisted_error_msg)
        return
    if resource.user_email:
        await message.answer(strings.take_taken_error_msg)
        return
    await message.answer("Напишите, где будет находится устройство? Например: Офис Екб, мой стол. Или: Питер, дома")
    await state.update_data(resource_id=resource_id)
    await state.set_state(TakeFSM.choosing_address)


@router.message(TakeFSM.choosing_address)
async def enter_address(message: Message, state: FSMContext) -> None:
    address = message.text.lower().strip()
    await state.update_data(address=address)
    await state.set_state(TakeFSM.choosing_return_date)
    await message.answer(
        text="Когда вернёте? Напишите примерную дату, например, 23.11.2024",
        reply_markup=SKIP_KEYBOARD)


@router.message(TakeFSM.choosing_return_date)
async def enter_return_date(message: Message, state: FSMContext) -> None:
    await fsmhelper.fill_date(
        message=message,
        state=state,
        next_state=TakeFSM.confirming,
        field_name=dbhelper.nameof(Resource.return_date),
        reply="Записываем на вас устройство?",
        keyboard=CONFIRM_OR_CANCEL_KEYBOARD,
        future_date=True
    )


@router.message(TakeFSM.confirming)
async def confirm_take(message: Message, state: FSMContext) -> None:
    if message.text.lower() == Buttons.CONFIRM.lower():
        user = await Visitor.get_current(message.chat.id)
        data = await state.get_data()
        resource_id = data["resource_id"]
        resource: Resource = await Resource.take(
            resource_id,
            user.email,
            data["address"],
            fsmhelper.restore_datetime(data["return_date"])
        )
        await Record.add(resource_id, user.email, ActionType.TAKE)
        await state.clear()
        await message.answer(
            text=f"На вас записано {resource.short_str()}. Приятного пользования!",
            reply_markup=ReplyKeyboardRemove()
        )
        logging.info(f"Пользователь {repr(user)} взял ресурс {repr(resource)}")
    elif message.text.lower() == Buttons.CANCEL.lower():
        await state.clear()
        await message.answer(
            text="Окей, устройство не записано на вас",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await message.answer(CHOOSE_CONFIRM_OR_CANCEL_MSG)
