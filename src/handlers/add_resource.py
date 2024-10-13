"""
Роутер для добавления ресурсов. Обрабатывает два важных сценария:
1. Загрузка файла с ресурсами в формате csv
2. Добавление ресурсов по одному (по полям, полям)
"""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardRemove

import handlers.strings
from database import dbhelper, resource_checker
from database.dbhelper import add_resource_from_df
from database.models import Category, Resource, Visitor
from handlers import strings
from handlers.strings import ResourceColumn
from helpers import fsmhelper, tghelper as tg, tghelper
from helpers.fileshelper import create_df_from_file
from helpers.fsmhelper import ADD_OR_CANCEL_KEYBOARD, Buttons, CANCEL_KEYBOARD, CHOOSE_ADD_OR_CANCEL_MSG, \
    SKIP_OR_CANCEL_KEYBOARD, fill_date, fill_str, fill_unique_field


class AddResourceFSM(StatesGroup):
    choosing = State()
    uploading = State()
    write_id = State()
    write_vendor_code = State()
    write_name = State()
    write_category = State()
    write_reg_date = State()
    write_firmware = State()
    write_comment = State()
    write_user_email = State()
    write_address = State()
    write_return_date = State()
    finish = State()


router = Router()


@router.message(Command("add"))
async def add_resource_command(message: Message, state: FSMContext) -> None:
    user = await Visitor.get_current(message.chat.id)
    if not user.is_admin:
        await message.answer(strings.not_found_msg)
        return
    await state.set_state(AddResourceFSM.choosing)
    await message.answer(
        text=strings.ask_upload_or_add_manually,
        reply_markup=tg.get_reply_keyboard([strings.manually_option, strings.file_option])
    )


@router.message(AddResourceFSM.choosing)
async def add_one_by_one_handler(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    if text == strings.manually_option:
        await state.set_state(AddResourceFSM.write_id)
        await state.set_data(Resource.get_fields())
        await message.answer(
            text=strings.ask_id,
            reply_markup=CANCEL_KEYBOARD
        )
    elif text == strings.file_option:
        await state.set_state(AddResourceFSM.uploading)
        await message.answer(
            text=strings.ask_file_msg,
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await message.answer(strings.ask_way_of_adding_msg)


@router.message(AddResourceFSM.write_id)
async def add_id(message: Message, state: FSMContext) -> None:
    if not message.text.strip().isnumeric():
        await message.answer(f"{handlers.strings.ResourceError.WRONG_ID.value}. {strings.ask_int_msg}")
        return
    await fill_unique_field(
        message,
        state,
        AddResourceFSM.write_vendor_code,
        dbhelper.nameof(Resource.id),
        strings.ask_vendor_code_msg,
        True
    )


@router.message(AddResourceFSM.write_vendor_code)
async def add_vendor_code(message: Message, state: FSMContext) -> None:
    await fill_unique_field(
        message,
        state,
        AddResourceFSM.write_name,
        dbhelper.nameof(Resource.vendor_code),
        strings.ask_name_msg,
        False
    )


@router.message(AddResourceFSM.write_name)
async def add_name(message: Message, state: FSMContext) -> None:
    await state.update_data({dbhelper.nameof(Resource.name): message.text.strip()})
    available_categories = [i.name for i in (await Category.get_all())]
    await state.set_state(AddResourceFSM.write_category)
    await message.answer(
        text=strings.ask_category_msg,
        reply_markup=tg.get_reply_keyboard(available_categories + [Buttons.CANCEL])
    )


@router.message(AddResourceFSM.write_category)
async def add_category(message: Message, state: FSMContext) -> None:
    category = message.text.strip()
    if not await resource_checker.is_right_category(category):
        await message.answer(f"{handlers.strings.ResourceError.WRONG_CATEGORY.value}. {strings.choose_option_msg}")
        return
    await state.update_data({dbhelper.nameof(Resource.category_name): category})
    await state.set_state(AddResourceFSM.write_reg_date)
    await message.answer(
        text=strings.ask_reg_date_msg,
        reply_markup=SKIP_OR_CANCEL_KEYBOARD
    )


@router.message(AddResourceFSM.write_reg_date)
async def add_reg_date(message: Message, state: FSMContext) -> None:
    await fill_date(
        message,
        state,
        AddResourceFSM.write_firmware,
        dbhelper.nameof(Resource.reg_date),
        strings.ask_firmware_msg,
        SKIP_OR_CANCEL_KEYBOARD,
        False
    )


@router.message(AddResourceFSM.write_firmware)
async def add_firmware(message: Message, state: FSMContext) -> None:
    await fill_str(
        message,
        state,
        AddResourceFSM.write_comment,
        dbhelper.nameof(Resource.firmware),
        strings.ask_comment_msg,
        SKIP_OR_CANCEL_KEYBOARD,
    )


@router.message(AddResourceFSM.write_comment)
async def add_comment(message: Message, state: FSMContext) -> None:
    await fill_str(
        message,
        state,
        AddResourceFSM.write_user_email,
        dbhelper.nameof(Resource.comment),
        strings.ask_email_msg,
        SKIP_OR_CANCEL_KEYBOARD
    )


@router.message(AddResourceFSM.write_user_email)
async def add_user_email(message: Message, state: FSMContext) -> None:
    user_email = message.text.strip()
    if Buttons.SKIP in user_email:
        await state.set_state(AddResourceFSM.finish)
        await message.answer(
            text=strings.confirm_adding_msg,
            reply_markup=ADD_OR_CANCEL_KEYBOARD
        )
        return
    else:
        if not resource_checker.is_kontur_email(user_email):
            await message.answer(handlers.strings.ResourceError.WRONG_EMAIL.value)
            return
    await state.update_data({dbhelper.nameof(Resource.user_email): user_email})
    await state.set_state(AddResourceFSM.write_address)
    await message.answer(
        text=strings.ask_address_msg,
        reply_markup=SKIP_OR_CANCEL_KEYBOARD
    )


@router.message(AddResourceFSM.write_address)
async def add_address(message: Message, state: FSMContext) -> None:
    await fill_str(
        message,
        state,
        AddResourceFSM.write_return_date,
        dbhelper.nameof(Resource.address),
        strings.ask_return_date_msg,
        SKIP_OR_CANCEL_KEYBOARD
    )


@router.message(AddResourceFSM.write_return_date)
async def add_return_date(message: Message, state: FSMContext) -> None:
    await fill_date(
        message,
        state,
        AddResourceFSM.finish,
        dbhelper.nameof(Resource.return_date),
        strings.confirm_adding_msg,
        ADD_OR_CANCEL_KEYBOARD,
        True
    )


@router.message(AddResourceFSM.finish)
async def finish_adding_resource(message: Message, state: FSMContext) -> None:
    command = message.text.strip()
    if command != Buttons.ADD:
        await message.answer(CHOOSE_ADD_OR_CANCEL_MSG)
        return
    data = await state.get_data()
    fields_and_values = {k: v for k, v in data.items() if k in Resource.get_fields_names()}
    return_date_field = dbhelper.nameof(Resource.return_date)
    reg_date_field = dbhelper.nameof(Resource.reg_date)
    fields_and_values.update(
        {
            return_date_field: fsmhelper.restore_datetime(fields_and_values[return_date_field]),
            reg_date_field: fsmhelper.restore_datetime(fields_and_values[reg_date_field])
        },
    )
    resource = await Resource.add(**fields_and_values)
    if not resource:
        await message.answer(f"{strings.manually_add_err_msg}. {strings.unexpected_action_msg}")
        return
    user_name = strings.get_username_str(message)
    logging.info(
        f"Пользователь{user_name}с chat_id {message.chat.id} добавил ресурс {repr(resource)}")
    await state.clear()
    await message.answer(
        text=f"{strings.manually_add_success_msg}\r\n\r\n{str(resource)}",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(AddResourceFSM.uploading, F.document)
async def paste_from_csv(message: Message, state: FSMContext) -> None:
    await message.answer(strings.file_is_processing_msg)
    in_memory_file = await tghelper.get_file_from_tg(message)
    df = await create_df_from_file(in_memory_file)
    if df is None:
        await message.answer(strings.wrong_file_format_msg)
        return
    if list(df.columns.values) != ResourceColumn.cols():
        await message.answer(f"{strings.incorrect_table_columns_msg} {ResourceColumn.cols_str()}")
        return

    errors = await resource_checker.check_table(df)
    if errors:
        await message.answer(f"{strings.table_errors_msg}\r\n\r\n{errors}")
        return

    await add_resource_from_df(df, message)
    await state.clear()
    await message.answer(strings.table_upload_success_msg, reply_markup=ReplyKeyboardRemove())


@router.message(AddResourceFSM.uploading, F.text)
async def wrong_text(message: Message, state: FSMContext) -> None:
    if message.text.casefold() == fsmhelper.Buttons.YES.casefold():
        await state.clear()
        await message.answer(text=strings.table_upload_cancelled_msg, reply_markup=ReplyKeyboardRemove())
        return
    elif message.text.casefold() == fsmhelper.Buttons.NO.casefold():
        await message.answer(text=strings.ask_table_again_msg, reply_markup=ReplyKeyboardRemove())
        return
    await message.answer(
        text=strings.ask_cancel_table_upload_msg,
        reply_markup=fsmhelper.YES_OR_NO_KEYBOARD
    )
