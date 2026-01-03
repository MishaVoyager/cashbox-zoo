import asyncio
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.memory import MemoryStorage
from configs.config import RedisConfig, Settings
from handlers import actions, add_resource, cancel, edit, developer, search, take, users
from middlewares.authenticate_middlware import Auth
from middlewares.service_provider_middleware import ServiceProvider
from middlewares.try_execute_middlware import TryExecuteInner
from middlewares.try_filter_middleware import TryFilterOuter
from service.database_service import DatabaseService
from service.orm_uow import OrmUnitOfWork


COMMANDS = [
    types.BotCommand(command="/all", description="Весь список устройств"),
    types.BotCommand(command="/categories", description="Поиск по рубрикам"),
    types.BotCommand(command="/mine", description="Мои устройства"),
    types.BotCommand(command="/wishlist", description="За какими устройствами вы в очереди"),
    types.BotCommand(command="/cancel", description="Вернуться к поиску по устройствам")
]


async def main(zoo_settings: Settings) -> None:
    uow = OrmUnitOfWork()
    db_service = DatabaseService(uow)
    await db_service.init()
    try:
        redis_config = RedisConfig()
        await start_bot(zoo_settings.token, redis_config.get_connection_str())
    except Exception:
        logging.error("Произошла неожиданная ошибка, приложение остановлено", exc_info=True)


async def start_bot(token: str, redis_connection_str: str) -> None:
    settings = Settings()
    bot = Bot(token=token)
    storage = RedisStorage.from_url(redis_connection_str) if settings.use_redis else MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.update.outer_middleware(ServiceProvider())
    dp.message.outer_middleware(Auth())
    dp.callback_query.outer_middleware(Auth())
    dp.message.outer_middleware(TryFilterOuter())
    dp.callback_query.outer_middleware(TryFilterOuter())
    dp.message.middleware(TryExecuteInner())
    dp.callback_query.middleware(TryExecuteInner())
    dp.include_routers(
        cancel.router, developer.router, users.router, add_resource.router,
        take.router, edit.router, actions.router, search.router
    )
    await bot.set_my_commands(COMMANDS)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types()
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    zoo_settings = Settings()
    asyncio.run(main(zoo_settings))
