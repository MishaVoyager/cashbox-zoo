"""
Модуль с методами проверки ресурса на содержание конкретных полей, уникальность и т.д

Classes
--------
ResourceError
    Енам содержит список ошибок при обработке ресурса и текстовое описание ошибки
"""
import re
from datetime import datetime
from re import Match
from typing import Optional

from database.models import Category, Resource, Visitor
from handlers import strings
from handlers.strings import ResourceColumn, id_doubles_prefix, vendor_code_doubles_prefix, ResourceError
import pandas as pd


async def is_admin(chat_id: int) -> bool:
    """Проверяет, является ли пользователь админом по значению в БД"""
    user = await Visitor.get_current(chat_id)
    return bool(user.is_admin)


def check_date(value: Optional[str], future_date: bool) -> bool:
    """Проверяет дату для устройства"""
    if not re.search(r"^\d{2}.\d{2}.\d{4}$", value):
        return False
    day, month, year = map(int, value.split("."))
    try:
        date = datetime(year, month, day)
    except ValueError:
        return False
    if future_date and date.date() < datetime.now().date():
        return False
    return True


def format_errors(indexes_with_errors: dict[int, list[ResourceError]]) -> str:
    """Выводит сообщение про ошибки в определенных строках"""
    errors_text = ""
    for row, errors in indexes_with_errors.items():
        errors_text += f"В строке {row}:\r\n" + "\r\n".join([i.value for i in errors]) + "\r\n\r\n"
    return errors_text


def try_convert_to_ddmmyyyy(date: str) -> Optional[datetime]:
    """
    Конвертирует текстовую строку в формате dd.mm.yyyy -
    в datetime, либо возвращает value_error
    """
    if not re.search(r"^\d{2}.\d{2}.\d{4}$", date):
        return None
    day, month, year = map(int, date.split("."))
    try:
        return datetime(year, month, day)
    except ValueError:
        return None


def is_valid_email(email: str) -> Optional[Match]:
    """Проверяет валидность email"""
    return re.search(r"^\w+@\w+\.\w+$", email)


def is_kontur_email(email: str) -> Optional[Match]:
    """Проверяет, что email - контуровский"""
    return re.search(r"^.*@((skbkontur)|(kontur))\.\w+$", email)


def is_paste_date(date: datetime) -> bool:
    """Проверяет, что дата из прошлого"""
    return date.date() < datetime.now().date()


async def is_right_category(category: str) -> bool:
    """Проверяет, что категория входит в список категорий в БД"""
    available_categories = [i.name for i in (await Category.get_all())]
    return category in available_categories


async def check_table(df: pd.DataFrame) -> str:
    """Проверяет таблицу с ресурсами и возвращает текст возникших ошибок"""
    available_categories = [i.name for i in (await Category.get_all())]
    resources = await Resource.get_all()
    existed_ids = [i.id for i in resources]
    existed_vendor_codes = [i.vendor_code for i in resources]
    df["id_valid"] = df.apply(lambda row: str(row[ResourceColumn.id.value]).isnumeric(), axis=1)
    df["vendor_valid"] = df.apply(lambda row: pd.notna(row[ResourceColumn.vendor_code.value]), axis=1)
    df["name_valid"] = df.apply(lambda row: pd.notna(row[ResourceColumn.name.value]), axis=1)
    df["cat_valid"] = df.apply(lambda row: str(row[ResourceColumn.category_name.value]) in available_categories, axis=1)

    df["reg_date_valid"] = df.apply(
        lambda row: check_date(str(row[ResourceColumn.reg_date.value]), False) if pd.notna(
            row[ResourceColumn.reg_date.value]) else True,
        axis=1)
    df["return_date_valid"] = df.apply(
        lambda row: check_date(str(row[ResourceColumn.return_date.value]), True) if pd.notna(
            row[ResourceColumn.return_date.value]) else True, axis=1)
    df["email_valid"] = df.apply(
        lambda row: bool(
            re.search(r"^.*@((skbkontur)|(kontur))\.\w+$", str(row[ResourceColumn.user_email.value]))) if pd.notna(
            row[ResourceColumn.user_email.value]) else True, axis=1)
    errors: list[str] = list()

    for index, row in df.iterrows():
        if row[ResourceColumn.id.value] in existed_ids:
            errors.append(strings.get_table_error_msg(index, ResourceError.EXISTED_ID))
        if row[ResourceColumn.vendor_code.value] in existed_vendor_codes:
            errors.append(strings.get_table_error_msg(index, ResourceError.EXISTED_VENDOR_CODE))
        if not row["id_valid"]:
            errors.append(strings.get_table_error_msg(index, ResourceError.WRONG_ID))
        if not row["vendor_valid"]:
            errors.append(strings.get_table_error_msg(index, ResourceError.NO_VENDOR_CODE))
        if not row["name_valid"]:
            errors.append(strings.get_table_error_msg(index, ResourceError.NO_NAME))
        if not row["cat_valid"]:
            errors.append(
                f"{strings.get_table_error_msg(index, ResourceError.WRONG_CATEGORY)}: {', '.join(available_categories)}"
            )
        if not row["reg_date_valid"]:
            errors.append(strings.get_table_error_msg(index, ResourceError.WRONG_REG_DATE))
        if not row["return_date_valid"]:
            errors.append(strings.get_table_error_msg(index, ResourceError.WRONG_REG_DATE))
        if not row["email_valid"]:
            errors.append(strings.get_table_error_msg(index, ResourceError.WRONG_EMAIL))
    id_doubles = df.duplicated(subset=[ResourceColumn.id.value])
    vendor_doubles = df.duplicated(subset=[ResourceColumn.vendor_code.value])
    if id_doubles.any():
        errors.append(f"{id_doubles_prefix}: {', '.join(map(str, [i + 2 for i, row in id_doubles.items() if row]))}")
    if vendor_doubles.any():
        errors.append(
            f"{vendor_code_doubles_prefix}: {', '.join(map(str, [i + 2 for i, row in vendor_doubles.items() if row]))}"
        )
    return "\r\n".join(errors)
