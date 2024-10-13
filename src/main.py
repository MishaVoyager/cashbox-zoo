import asyncio
import logging
from logging.handlers import TimedRotatingFileHandler

from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

import database.dbhelper as dbhelper
from configs.config import RedisConfig, Settings, WebhookSettings
from handlers import actions, add_resource, auth, cancel, edit, info, search, take, users

COMMANDS = [
    types.BotCommand(command="/all", description="Весь список устройств"),
    types.BotCommand(command="/categories", description="Поиск по рубрикам"),
    types.BotCommand(command="/mine", description="Мои устройства"),
    types.BotCommand(command="/wishlist", description="За какими устройствами вы в очереди"),
    types.BotCommand(command="/help", description="Как пользоваться ботом?")
]


async def main(settings: Settings) -> None:
    await dbhelper.init_base()
    if settings.test_data:
        await dbhelper.prepare_test_data()
    try:
        await start_bot(settings)
    except Exception:
        logging.error("Произошла неожиданная ошибка, приложение остановлено", exc_info=True)


async def start_bot(settings: Settings) -> None:
    """Запускает бота в режиме поллинга или вебхука в зависимости от переменной среды"""
    bot = Bot(token=settings.token)
    storage = RedisStorage.from_url(RedisConfig().get_connection_str())
    dp = Dispatcher(storage=storage)
    dp.include_routers(
        cancel.router, info.router, users.router, auth.router, add_resource.router,
        take.router, edit.router, actions.router, search.router
    )
    await bot.set_my_commands(COMMANDS)
    await bot.delete_webhook(drop_pending_updates=True)
    if settings.use_polling:
        logging.info("Приложение запустилось в режиме polling")
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types()
        )
    else:
        await start_webhook(bot, dp)


async def start_webhook(bot: Bot, dp: Dispatcher) -> None:
    """Запускает приложение в режиме вебкуха"""
    webhook_settings = WebhookSettings()
    webhook_route = "/webhook"
    webhook_url = f"{webhook_settings.zoo_webhook_path}{webhook_route}"
    logging.info(f"Телеграму передан адрес вебхука: {webhook_url}")
    await bot.set_webhook(webhook_url, secret_token=webhook_settings.webhook_secret)
    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot,
                                                    secret_token=webhook_settings.webhook_secret)
    webhook_requests_handler.register(app, path=webhook_route)
    setup_application(app, dp, bot=bot)
    logging.info(
        f"Приложение запустилось на сервере. Хост: {webhook_settings.zoo_host}, порт: {webhook_settings.zoo_port}. "
        f"URL вебхука: {webhook_url}")
    await web._run_app(app, host=webhook_settings.zoo_host, port=webhook_settings.zoo_port)


if __name__ == "__main__":
    settings = Settings()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    if settings.write_logs_in_file:
        handler = TimedRotatingFileHandler(
            filename="logs/cashbox_zoo.log",
            when="midnight",
            backupCount=30,
            encoding="utf-8",
            utc=True
        )
        logging.getLogger().addHandler(handler)
    asyncio.run(main(settings))
