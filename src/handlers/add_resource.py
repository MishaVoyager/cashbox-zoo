"""
Роутер для добавления ресурсов. Обрабатывает два важных сценария:
1. Загрузка файла с ресурсами в формате csv или эксель
2. Добавление ресурсов по одному (по полям, полям)
"""
import datetime
import logging

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery
from aiogram_calendar import SimpleCalendarCallback

from configs.config import Settings
from domain.models import Resource, Visitor, Record
from helpers import fsmhelper, tghelper as tg, tghelper
from helpers.fsmhelper import ADD_OR_CANCEL_KEYBOARD, Buttons, CANCEL_KEYBOARD, CHOOSE_ADD_OR_CANCEL_MSG, \
    SKIP_OR_CANCEL_KEYBOARD, fill_date_from_calendar, fill_str, handle_text_instead_of_date_from_calendar
from helpers.tghelper import start_calendar, nameof
from middlewares.authorize_middleware import Authorize
from resources import strings
from resources.strings import ResourceColumn
from service import resource_checker
from service.services import ResourceService
from service.table_helper import load_file_to_df, check_table, convert_to_models


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
router.message.middleware(Authorize())
router.callback_query.middleware(Authorize())


@router.message(Command("add"))
async def add_resource_command(message: Message, state: FSMContext) -> None:
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
async def add_id(message: Message, state: FSMContext, visitor: Visitor, resource_service: ResourceService) -> None:
    if not message.text.strip().isnumeric():
        await message.answer(f"{strings.ResourceError.WRONG_ID.value}. {strings.ask_int_msg}")
        return
    resource_id = int(message.text.strip())
    get_result = await resource_service.get(resource_id)
    if get_result.is_success:
        existed_resource = get_result.unwrap()
        await state.clear()
        await message.answer(
            text=f"Уже есть устройство с таким id: \n\n{existed_resource.description()}",
            reply_markup=ReplyKeyboardRemove())
        return
    await state.update_data({nameof(Resource.id): resource_id})
    await state.set_state(AddResourceFSM.write_vendor_code)
    await message.answer(
        text=strings.ask_vendor_code_msg,
        reply_markup=CANCEL_KEYBOARD
    )


@router.message(AddResourceFSM.write_vendor_code)
async def add_vendor_code(message: Message, state: FSMContext, visitor: Visitor,
                          resource_service: ResourceService) -> None:
    vendor_code = message.text.strip()
    get_result = await resource_service.get_by_vendor_code(vendor_code)
    if get_result.is_success:
        existed_resource = get_result.unwrap()
        await state.clear()
        await message.answer(
            text=f"Уже есть устройство с таким артикулом: \n\n{existed_resource.description()}",
            reply_markup=ReplyKeyboardRemove())
        return
    await state.update_data({nameof(Resource.vendor_code): vendor_code})
    await state.set_state(AddResourceFSM.write_name)
    await message.answer(
        text=strings.ask_name_msg,
        reply_markup=CANCEL_KEYBOARD
    )


@router.message(AddResourceFSM.write_name)
async def add_name(message: Message, state: FSMContext) -> None:
    await state.update_data({nameof(Resource.name): message.text.strip()})
    categories = Settings().get_categories()
    await state.set_state(AddResourceFSM.write_category)
    await message.answer(
        text=strings.ask_category_msg,
        reply_markup=tg.get_reply_keyboard(categories + [Buttons.CANCEL])
    )


@router.message(AddResourceFSM.write_category)
async def add_category(message: Message, state: FSMContext) -> None:
    category = message.text.strip()
    if category not in Settings().get_categories():
        await message.answer(f"{strings.ResourceError.WRONG_CATEGORY.value}. {strings.choose_option_msg}")
        return
    await state.update_data({nameof(Resource.category_name): category})
    await state.set_state(AddResourceFSM.write_firmware)
    await message.answer(
        text=strings.ask_firmware_msg,
        reply_markup=SKIP_OR_CANCEL_KEYBOARD
    )


@router.message(AddResourceFSM.write_firmware)
async def add_firmware(message: Message, state: FSMContext) -> None:
    await fill_str(
        message,
        state,
        AddResourceFSM.write_reg_date,
        nameof(Resource.firmware),
        strings.ask_reg_date_msg,
        await start_calendar()
    )


@router.callback_query(SimpleCalendarCallback.filter(), StateFilter(AddResourceFSM.write_reg_date))
async def add_reg_date(call: CallbackQuery, callback_data: CallbackData, state: FSMContext) -> None:
    await fill_date_from_calendar(
        call,
        callback_data,
        state,
        AddResourceFSM.write_comment,
        nameof(Resource.reg_date),
        strings.ask_comment_msg,
        SKIP_OR_CANCEL_KEYBOARD,
        False
    )


@router.message(AddResourceFSM.write_reg_date)
async def message_instead_of_date_handler_for_reg_date(message: Message, state: FSMContext) -> None:
    await handle_text_instead_of_date_from_calendar(
        message,
        state,
        AddResourceFSM.write_comment,
        nameof(Resource.reg_date),
        strings.ask_comment_msg,
        SKIP_OR_CANCEL_KEYBOARD
    )


@router.message(AddResourceFSM.write_comment)
async def add_comment(message: Message, state: FSMContext) -> None:
    await fill_str(
        message,
        state,
        AddResourceFSM.write_user_email,
        nameof(Resource.comment),
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
            await message.answer(strings.ResourceError.WRONG_EMAIL.value)
            return
    await state.update_data({nameof(Record.user_email): user_email})
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
        nameof(Record.address),
        strings.ask_return_date_from_calendar_msg,
        await start_calendar()
    )


@router.callback_query(SimpleCalendarCallback.filter(), StateFilter(AddResourceFSM.write_return_date))
async def add_return_date(call: CallbackQuery, callback_data: CallbackData, state: FSMContext) -> None:
    await fill_date_from_calendar(
        call,
        callback_data,
        state,
        AddResourceFSM.finish,
        nameof(Record.return_date),
        strings.confirm_adding_msg,
        ADD_OR_CANCEL_KEYBOARD,
        True
    )


@router.message(AddResourceFSM.write_return_date)
async def message_instead_of_date_handler(message: Message, state: FSMContext) -> None:
    await handle_text_instead_of_date_from_calendar(
        message,
        state,
        AddResourceFSM.finish,
        nameof(Record.return_date),
        strings.confirm_adding_msg,
        ADD_OR_CANCEL_KEYBOARD,
    )


@router.message(AddResourceFSM.finish)
async def finish_adding_resource(
        message: Message,
        state: FSMContext,
        resource_service: ResourceService
) -> None:
    command = message.text.strip()
    if command != Buttons.ADD:
        await message.answer(CHOOSE_ADD_OR_CANCEL_MSG)
        return
    data = await state.get_data()
    resource = Resource(
        id=data["id"],
        name=data["name"],
        category_name=data["category_name"],
        vendor_code=data["vendor_code"],
        reg_date=None if "reg_date" not in data else fsmhelper.restore_datetime(data["reg_date"]),
        firmware=None if "firmware" not in data else data["firmware"],
        comment=None if "comment" not in data else data["comment"]
    )
    take_record = None if "user_email" not in data else Record(
        resource_id=data["id"],
        user_email=data["user_email"],
        address=data["address"],
        take_date=datetime.datetime.now(),
        return_date=fsmhelper.restore_datetime(data["return_date"])
    )
    result = await resource_service.add_with_record(resource, take_record)
    if result.is_failure:
        await message.answer(f"{strings.manually_add_err_msg}. {strings.unexpected_action_msg}")
        return
    user_name = strings.get_username_str(message)
    logging.info(
        f"Пользователь{user_name}с chat_id {message.chat.id} добавил ресурс {repr(resource)}")
    await state.clear()
    await message.answer(
        text=f"{strings.manually_add_success_msg}",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(AddResourceFSM.uploading, F.document)
async def paste_from_file(message: Message, state: FSMContext, resource_service: ResourceService) -> None:
    await message.answer(f"{strings.Emoji.FINGERS_CROSSED.value}")
    await message.answer(strings.file_is_processing_msg)
    in_memory_file = await tghelper.get_file_from_tg(message)
    # TODO обработка этих ошибок - ответственность специального сервиса
    df = await load_file_to_df(in_memory_file)
    if df is None:
        await message.answer(strings.wrong_file_format_msg)
        return
    if list(df.columns.values) != ResourceColumn.cols():
        await message.answer(f"{strings.incorrect_table_columns_msg} {ResourceColumn.cols_str()}")
        return
    resources = (await resource_service.get_all()).unwrap()
    df, errors = await check_table(
        df=df,
        existed_resource_ids=[i.id for i in resources],
        existed_vendor_codes=[i.vendor_code for i in resources]
    )
    if errors:
        await message.answer(f"{strings.table_errors_msg}\r\n\r\n{errors}")
        return

    resources_with_take_records = convert_to_models(df)
    result = await resource_service.add_many_with_record(resources_with_take_records)
    if result.is_failure:
        await message.answer("Ошибка при загрузке данных. Загрузка отменена")
        return
    await state.clear()
    await message.answer(f"{strings.Emoji.CHAMPAGNE.value}", reply_markup=ReplyKeyboardRemove())
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
