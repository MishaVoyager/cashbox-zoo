"""
Методы для работы с файлами (csv, excel)
"""

import io
import logging
from typing import BinaryIO, Optional

import pandas as pd

from charset_normalizer import from_bytes


def get_charset(file: BinaryIO) -> str:
    """Возвращает кодировку, одну из двух: cp1251 или utf_8"""
    charset = from_bytes(file.read()).best().encoding
    logging.info(f"Charset normalizer определил кодировку как: {charset}")
    if charset not in ["cp1251", "utf_8"]:
        charset = "cp1251"
    logging.info(f"Для декодирования выбрана кодировка: {charset}")
    file.seek(0)
    return charset


async def create_df_from_file(in_memory_file: BinaryIO) -> Optional[pd.DataFrame]:
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
