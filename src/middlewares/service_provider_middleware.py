from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject, CallbackQuery

from service.database_service import DatabaseService
from service.orm_uow import OrmUnitOfWork
from service.services import CategoryService, ResourceService, VisitorService, RecordService
from service.notification_service import NotificationService


class ServiceProvider(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: Message | CallbackQuery,
            data: Dict[str, Any]
    ) -> Any:
        uow = OrmUnitOfWork()
        category_service = CategoryService(uow)
        resource_service = ResourceService(uow)
        visitor_service = VisitorService(uow)
        record_service = RecordService(uow)
        notification_service = NotificationService(uow)
        database_service = DatabaseService(uow)

        data["uow"] = uow
        data["category_service"] = category_service
        data["resource_service"] = resource_service
        data["visitor_service"] = visitor_service
        data["record_service"] = record_service
        data["notification_service"] = notification_service
        data["database_service"] = database_service
        return await handler(event, data)
