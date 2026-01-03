import io
import logging
import re
from datetime import datetime as dt
from typing import List, Tuple, Optional, Any, BinaryIO

import pandas as pd
from charset_normalizer import from_bytes

from configs.config import Settings
from domain.models import Resource, Record
from resources import strings
from resources.strings import ResourceColumn, ResourceError
from service import resource_checker


def convert_to_models(df: pd.DataFrame) -> List[Tuple[Resource, Optional[Record]]]:
    result = []
    for index, row in df.iterrows():
        resource = Resource(
            id=int(row[ResourceColumn.id.value]),
            name=str(row[ResourceColumn.name.value]),
            category_name=str(row[ResourceColumn.category_name.value]),
            vendor_code=str(row[ResourceColumn.vendor_code.value]),
            reg_date=resource_checker.try_convert_to_ddmmyyyy(
                str(row[ResourceColumn.reg_date.value])) if row_have_content(
                row[ResourceColumn.reg_date.value]) else None,
            firmware=row[ResourceColumn.firmware.value] if row_have_content(
                row[ResourceColumn.firmware.value]) else None,
            comment=row[ResourceColumn.comment.value] if row_have_content(
                row[ResourceColumn.comment.value]) else None
        )
        user_email = row[ResourceColumn.user_email.value] if row_have_content(
            row[ResourceColumn.user_email.value]) else None
        address = row[ResourceColumn.address.value] if row_have_content(
            row[ResourceColumn.address.value]) else None
        return_date = resource_checker.try_convert_to_ddmmyyyy(
            str(row[ResourceColumn.return_date.value])) if row_have_content(
            row[ResourceColumn.return_date.value]) else None
        record = None
        if user_email:
            record = Record(
                resource_id=resource.id,
                user_email=user_email,
                address=address,
                take_date=dt.now(),
                return_date=return_date
            )
        result.append((resource, record))
    return result


def row_have_content(obj: Any) -> bool:
    return pd.notna(obj) and str(obj).strip() != ''


async def check_table(
        df: pd.DataFrame,
        existed_resource_ids: List[int],
        existed_vendor_codes: List[str]
) -> Tuple[pd.DataFrame, str]:
    """Проверяет таблицу с ресурсами и возвращает текст возникших ошибок"""
    categories = Settings().get_categories()
    df["id_valid"] = df.apply(lambda row: str(row[ResourceColumn.id.value]).isnumeric(), axis=1)
    df["name_valid"] = df.apply(lambda row: row_have_content(row[ResourceColumn.name.value]), axis=1)
    df["cat_valid"] = df.apply(lambda row: str(row[ResourceColumn.category_name.value]) in categories, axis=1)
    df["vendor_valid"] = df.apply(lambda row: row_have_content(row[ResourceColumn.vendor_code.value]), axis=1)
    df["reg_date_valid"] = df.apply(
        lambda row: resource_checker.check_date(str(row[ResourceColumn.reg_date.value]),
                                                False) if row_have_content(
            row[ResourceColumn.reg_date.value]) else True,
        axis=1)

    df["return_date_valid"] = df.apply(
        lambda row: resource_checker.check_date(str(row[ResourceColumn.return_date.value]),
                                                True) if row_have_content(
            row[ResourceColumn.return_date.value]) else True, axis=1)
    df["email_valid"] = df.apply(
        lambda row: bool(
            re.search(r"^.*@((skbkontur)|(kontur))\.\w+$",
                      str(row[ResourceColumn.user_email.value]))) if row_have_content(
            row[ResourceColumn.user_email.value]) else True, axis=1)
    errors: list[str] = list()

    for index, row in df.iterrows():
        if row[ResourceColumn.id.value] in existed_resource_ids:
            errors.append(strings.get_table_error_msg(index, ResourceError.EXISTED_ID))
        if str(row[ResourceColumn.vendor_code.value]) in existed_vendor_codes:
            errors.append(strings.get_table_error_msg(index, ResourceError.EXISTED_VENDOR_CODE))
        if not row["id_valid"]:
            errors.append(strings.get_table_error_msg(index, ResourceError.WRONG_ID))
        if not row["vendor_valid"]:
            errors.append(strings.get_table_error_msg(index, ResourceError.NO_VENDOR_CODE))
        if not row["name_valid"]:
            errors.append(strings.get_table_error_msg(index, ResourceError.NO_NAME))
        if not row["cat_valid"]:
            errors.append(
                f"{strings.get_table_error_msg(index, ResourceError.WRONG_CATEGORY)}: {', '.join(categories)}"
            )
        if not row["reg_date_valid"]:
            errors.append(strings.get_table_error_msg(index, ResourceError.WRONG_REG_DATE))
        if not row["return_date_valid"]:
            errors.append(strings.get_table_error_msg(index, ResourceError.WRONG_RETURN_DATE))
        if not row["email_valid"]:
            errors.append(strings.get_table_error_msg(index, ResourceError.WRONG_EMAIL))
    id_doubles = df.duplicated(subset=[ResourceColumn.id.value])
    vendor_doubles = df.duplicated(subset=[ResourceColumn.vendor_code.value])
    if id_doubles.any():
        errors.append(
            f"{strings.id_doubles_prefix}: {', '.join(map(str, [i + 2 for i, row in id_doubles.items() if row]))}")
    if vendor_doubles.any():
        errors.append(
            f"{strings.vendor_code_doubles_prefix}: {', '.join(map(str, [i + 2 for i, row in vendor_doubles.items() if row]))}"
        )
    return df, "\r\n".join(errors)


def get_charset(file: BinaryIO) -> str:
    """Возвращает кодировку, одну из двух: cp1251 или utf_8"""
    charset = from_bytes(file.read()).best().encoding
    logging.info(f"Charset normalizer определил кодировку как: {charset}")
    if charset not in ["cp1251", "utf_8"]:
        charset = "cp1251"
    logging.info(f"Для декодирования выбрана кодировка: {charset}")
    file.seek(0)
    return charset


async def load_file_to_df(in_memory_file: BinaryIO) -> Optional[pd.DataFrame]:
    """Создает dataframe на основе csv или excel-файла, загруженного в память"""
    file_extension = in_memory_file.name.split(".")[-1]
    if file_extension == "csv":
        charset = get_charset(in_memory_file)
        s = io.StringIO(in_memory_file.read().decode(encoding=charset))
        return pd.read_csv(s)
    elif "xls" in file_extension:
        excel_data = pd.ExcelFile(io.BytesIO(in_memory_file.read()))
        return excel_data.parse(excel_data.sheet_names[-1])
    else:
        return None
