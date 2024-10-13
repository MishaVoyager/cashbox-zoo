"""
Роутер для отмены. Позволяет выйти из любого сценария текстом cancel / отмена / отменить.
Удобно определить в одном месте, чтобы не делать это в каждом роутере.
Также это подстраховка для сценария, в котором пользователь заблокируется.
"""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from handlers import strings

router = Router()


@router.message(Command("cancel"))
@router.message(F.text.casefold().contains("отменить"))
@router.message(F.text.casefold().contains("отмена"))
async def cancel_handler(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if not current_state:
        return
    await state.clear()
    await message.answer(strings.cancel_msg, reply_markup=ReplyKeyboardRemove())
