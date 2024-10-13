import datetime
import logging
from typing import Optional, List, Any

import httpx

from configs import config

CONFIG = config.Settings()
PASSPORT_URL = ""
STAFF_URL = ""


async def get_staff_token() -> Optional[str]:
    pass


async def search_emails(query: str) -> Optional[List[str]]:
    pass


async def get_dismissed_users_emails(from_days_ago: int) -> set[Any]:
    pass
