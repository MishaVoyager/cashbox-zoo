"""
Настройки - при помощи pydantic-settings подтягиваются в классы конфигов

Classes
--------
WebhookSettings
    Настройки для вебкуха (для режима поллинга не нужны)
PostgresSettings
    Настройки для подключения к БД
Settings
    Общие настройки приложения
"""

import re
from os import getenv
from typing import Optional, List

from arq.connections import RedisSettings
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SECRETS_ADDRESS = getenv("SECRETS_ADDRESS")


class Settings(BaseSettings):
    """Общие настройки приложения"""
    model_config = SettingsConfigDict(
        secrets_dir=SECRETS_ADDRESS,
        env_file='.env',
        env_file_encoding='utf-8',
        extra="allow"
    )

    token: str
    use_redis: bool
    zoo_admin_pass: str
    admins: str
    categories: str
    locale_for_calendar: str = "ru_RU.UTF-8"
    # Указана локаль для запуска в докере.
    # При запуске бота локально указать то, что возвращает print(locale.getlocale())
    staff_client_id: str
    staff_client_secret: str
    secrets_address: Optional[str] = None

    def get_categories(self) -> List[str]:
        return self.categories.split(", ")

    @field_validator("categories")
    @classmethod
    def check_categories(cls, categories: str) -> str:
        if categories.strip() == "":
            raise ValueError("Список категорий не должен быть пустым")
        cats = [i.capitalize() for i in categories.strip().split(", ")]
        if len(set(cats)) != len(cats):
            raise ValueError("В списке категорий (categories) не должно быть одинаковых элементов")
        return ", ".join(cats)

    @field_validator("admins")
    @classmethod
    def check_admin_emails(cls, emails: str) -> str:
        if emails.strip() == "":
            raise ValueError("Список почт админов (emails) не должен быть пустым")

        for email in emails.strip().split():
            if not re.search(r"^.*@((skbkontur)|(kontur))\.\w+$", email):
                raise ValueError("В переменной среды Admins должны быть контуровские почты админов")
        return emails


class RedisConfig(BaseSettings):
    model_config = SettingsConfigDict(
        secrets_dir=SECRETS_ADDRESS,
        env_file='.env',
        env_file_encoding='utf-8',
        extra="allow"
    )

    redis_host: str
    redis_port: int
    redis_databases: int

    def get_connection_str(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_databases}"

    def get_pool_settings(self) -> RedisSettings:
        return RedisSettings(
            host=self.redis_host,
            port=self.redis_port,
            database=self.redis_databases,
        )


class PostgresSettings(BaseSettings):
    """Настройки для подключения к БД"""
    model_config = SettingsConfigDict(
        secrets_dir=SECRETS_ADDRESS,
        env_file='.env',
        env_file_encoding='utf-8',
        extra="allow"
    )

    pg_connection_str: str
