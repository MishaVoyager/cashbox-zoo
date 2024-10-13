from datetime import datetime
from typing import Optional

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, ReplyKeyboardRemove

import handlers.strings
from database import dbhelper, resource_checker
from database.models import Resource
from handlers import strings
from helpers import tghelper as tg


class Buttons:
    CANCEL = "Отменить"
    SKIP = "Пропустить"
    ADD = "Добавить"
    CONFIRM = "Подтвердить"
    RETURN = "Вернуться назад"
    YES = "Да"
    NO = "Нет"


YES_OR_NO_KEYBOARD = tg.get_reply_keyboard([Buttons.YES, Buttons.NO])
CANCEL_KEYBOARD = tg.get_reply_keyboard([Buttons.CANCEL])
SKIP_KEYBOARD = tg.get_reply_keyboard([Buttons.SKIP])
RETURN_KEYBOARD = tg.get_reply_keyboard([Buttons.RETURN])

CONFIRM_OR_CANCEL_KEYBOARD = tg.get_reply_keyboard([Buttons.CONFIRM, Buttons.CANCEL])
CONFIRM_OR_RETURN_KEYBOARD = tg.get_reply_keyboard([Buttons.CONFIRM, Buttons.RETURN])
SKIP_OR_RETURN_KEYBOARD = tg.get_reply_keyboard([Buttons.SKIP, Buttons.RETURN])
SKIP_OR_CANCEL_KEYBOARD = tg.get_reply_keyboard([Buttons.SKIP, Buttons.CANCEL])
ADD_OR_CANCEL_KEYBOARD = tg.get_reply_keyboard([Buttons.ADD, Buttons.CANCEL])

CHOOSE_CONFIRM_OR_RETURN_MSG = f"Выберите, {Buttons.CONFIRM} или {Buttons.RETURN}"
CHOOSE_CONFIRM_OR_CANCEL_MSG = f"Выберите, {Buttons.CONFIRM} или {Buttons.CANCEL}"
CHOOSE_ADD_OR_CANCEL_MSG = f"Выберите, {Buttons.ADD} или {Buttons.CANCEL}"


async def fill_str(
        message: Message,
        state: FSMContext,
        next_state: State,
        field_name: str,
        text: str,
        reply_markup: ReplyKeyboardMarkup
) -> None:
    value = message.text.strip()
    if Buttons.SKIP in value:
        value = None
    await state.update_data({field_name: value})
    await state.set_state(next_state)
    await message.answer(text=text, reply_markup=reply_markup)


async def fill_unique_field(
        message: Message,
        state: FSMContext,
        next_state: State,
        field_name: str,
        reply: str,
        to_int: bool
) -> None:
    field_value = int(message.text) if to_int else message.text
    existed_resources: list[Resource] = await Resource.get({field_name: field_value})
    if len(existed_resources) >= 1:
        await state.clear()
        await message.answer(
            text=f"Уже есть устройства с таким значением. Отредактировать их можно командой "
                 f"edit\r\n\r\n{await dbhelper.format_notes(existed_resources, message.chat.id)}",
            reply_markup=ReplyKeyboardRemove())
        return
    await state.update_data({field_name: field_value})
    await state.set_state(next_state)
    await message.answer(
        text=reply,
        reply_markup=CANCEL_KEYBOARD
    )


def restore_datetime(date: Optional[tuple[int, int, int]]) -> Optional[datetime]:
    if date is None:
        return None
    return datetime(year=date[0], month=date[1], day=date[2])


async def fill_date(
        message: Message,
        state: FSMContext,
        next_state: State,
        field_name: str,
        reply: str,
        keyboard: ReplyKeyboardMarkup,
        future_date: bool
) -> None:
    field_value = message.text.strip()
    if Buttons.SKIP in field_value:
        date = None
    else:
        date = resource_checker.try_convert_to_ddmmyyyy(field_value)
        if not date:
            await message.answer(handlers.strings.ResourceError.WRONG_DATE.value)
            return
        if future_date and resource_checker.is_paste_date(date):
            await message.answer(strings.pass_date_error_msg)
            return
    date_suitable_for_redis = None if date is None else (date.year, date.month, date.day)
    await state.update_data({field_name: date_suitable_for_redis})
    await state.set_state(next_state)
    await message.answer(text=reply, reply_markup=keyboard)


async def turn_next_state(state: FSMContext, group: StatesGroup) -> None:
    """
    Не рекомендуется использовать, поскольку содержит перебор стейтов O(n),
    а также потому, что выбор стейта будет неявным
    """
    state_name = await state.get_state()
    states = list(group.__state_names__)  # type: ignore
    next_state_index = -1
    for i, s in enumerate(states):
        if s == state_name:
            next_state_index = i + 1
            break
    if next_state_index != -1 and next_state_index < len(states):
        await state.set_state(states[next_state_index])
    else:
        raise ValueError(f"Не найден текущий стейт {state_name} или следующий. Индекс: {next_state_index}")
