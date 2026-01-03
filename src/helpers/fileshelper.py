"""
Методы для работы с файлами (csv, excel)
"""

import io
import logging
from typing import BinaryIO, Optional

import pandas as pd
from charset_normalizer import from_bytes



