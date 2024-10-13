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
from typing import Optional

from arq.connections import RedisSettings
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SECRETS_ADDRESS = getenv("SECRETS_ADDRESS")


class WebhookSettings(BaseSettings):
    """Настройки для вебкуха (не используются при поллинге)"""
    model_config = SettingsConfigDict(
        secrets_dir=SECRETS_ADDRESS,
        env_file='.env',
        env_file_encoding='utf-8',
        extra="allow"
    )

    zoo_webhook_path: Optional[str] = None
    webhook_secret: Optional[str] = None
    zoo_host: Optional[str] = None
    zoo_port: Optional[int] = None


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

    postgres_url: str
    pg_db_name: str
    pg_user: str
    pg_pass: str

    def get_connection_str(self) -> str:
        return f"postgresql+asyncpg://{self.pg_user}:{self.pg_pass}@{self.postgres_url}/{self.pg_db_name}"


class Settings(BaseSettings):
    """Общие настройки приложения"""
    model_config = SettingsConfigDict(
        secrets_dir=SECRETS_ADDRESS,
        env_file='.env',
        env_file_encoding='utf-8',
        extra="allow"
    )

    use_polling: bool
    secrets_address: Optional[str] = None
    write_logs_in_file: bool
    token: str
    zoo_admin_pass: str
    admins: str
    test_data: bool
    staff_client_id: str
    staff_client_secret: str

    @field_validator("admins")
    def check_admin_emails(cls, emails: str) -> str:
        result = True
        for email in emails.split():
            if not re.search(r"^.*@((skbkontur)|(kontur))\.\w+$", email):
                result = False
        if not result:
            raise ValueError("В переменной среды Admins должны быть контуровские почты админов")
        else:
            return emails
