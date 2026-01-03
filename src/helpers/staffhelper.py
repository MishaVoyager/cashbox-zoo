import datetime
import logging
from typing import Optional, List, Any

import httpx

from configs import config

CONFIG = config.Settings()
PASSPORT_URL = "https://passport.skbkontur.ru"
STAFF_URL = "https://staff.skbkontur.ru"


async def get_staff_token() -> Optional[str]:
    """Получает в паспорте токен для запросов в АПИ Стаффа"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{PASSPORT_URL}/connect/token",
            data={
                "grant_type": "client_credentials",
                "scope": "profiles",
            },
            auth=httpx.BasicAuth(CONFIG.staff_client_id, CONFIG.staff_client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        logging.error(f"Ошибка при запросе токена: {response.status_code}")
        return None


async def search_emails(query: str) -> Optional[List[str]]:
    """Ищет по всей инфе о сотруднике в Стаффе и возвращает почты действующих сотрудников"""
    token = await get_staff_token()
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{STAFF_URL}/api/Suggest/bytype",
            params={"Q": query, "Types": 7},
            headers={"Authorization": f"Bearer {token}"},
        )
    if response.status_code == 200:
        data = response.json()["items"]
        if len(data) == 0:
            return []
        else:
            return [item["email"] for item in data if item["status"] != "dismissed"]
    else:
        logging.error(f"Ошибка при поиске пользователей: {response.status_code}")
        return None


async def get_dismissed_users_emails(from_days_ago: int) -> set[Any]:
    if from_days_ago >= 7:
        raise ValueError("Данный метод подходит, только если мы берем обновления максимум за 7 дней")
    from_date = datetime.datetime.now() - datetime.timedelta(days=from_days_ago)
    token = await get_staff_token()
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{STAFF_URL}/api/Users/patch",
            params={"LastModifedDate": str(from_date)},
            headers={"Authorization": f"Bearer {token}"},
        )
    if response.status_code != 200:
        logging.error(f"Ошибка при получении уволенных пользователей: {response.status_code} {response.json()}")
        return set()
    fired_users = response.json()["firedUsers"]
    return set([i["email"] for i in fired_users])
