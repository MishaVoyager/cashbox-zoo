import logging
import traceback
from abc import ABC
from types import TracebackType
from typing import Optional, Type, Any

from sqlalchemy.ext.asyncio import AsyncSession, AsyncSessionTransaction

from database.engine import get_session_factory
from database.orm_repository import OrmResourceRepository, OrmVisitorRepository, OrmRecordRepository, \
    OrmCategoryRepository, OrmDatabaseRepository
from database.uow import UnitOfWork


class OrmUnitOfWork(UnitOfWork, ABC):
    def __init__(self) -> None:
        self.session_factory = get_session_factory()
        self.session: Optional[AsyncSession] = None
        self.transaction: Optional[AsyncSessionTransaction] = None

    async def __aenter__(self) -> 'OrmUnitOfWork':
        self.session = self.session_factory()
        self._resources = OrmResourceRepository(self.session)
        self._visitors = OrmVisitorRepository(self.session)
        self._records = OrmRecordRepository(self.session)
        self._categories = OrmCategoryRepository(self.session)
        self._database = OrmDatabaseRepository(self.session)
        self.transaction = await self.session.begin()
        return self

    async def __aexit__(
            self,
            exc_type: Optional[Type[BaseException]],
            exc_val: Optional[BaseException],
            exc_tb: Optional[TracebackType]) -> None:
        try:
            if exc_type:
                logging.error(f"Откатили транзакцию из-за ошибки: {str(exc_type)} {exc_val}\n{traceback.format_exc()}")
                await self.rollback()
                # если здесь вернуть true - ошибка не выкинется на уровень выше
            else:
                await self.commit()
        finally:
            await self.session.close()

    async def commit(self) -> None:
        if self.transaction and self.transaction.is_active:
            await self.transaction.commit()

    async def rollback(self) -> None:
        if self.transaction and self.transaction.is_active:
            await self.transaction.rollback()

    async def merge(self, object: Any) -> Any:
        return await self.session.merge(object)

    @property
    def resources(self) -> OrmResourceRepository:
        return self._resources

    @resources.setter
    def resources(self, resources: OrmResourceRepository) -> None:
        self._resources = resources

    @property
    def visitors(self) -> OrmVisitorRepository:
        return self._visitors

    @visitors.setter
    def visitors(self, visitors: OrmVisitorRepository) -> None:
        self._visitors = visitors

    @property
    def records(self) -> OrmRecordRepository:
        return self._records

    @records.setter
    def records(self, records: OrmRecordRepository) -> None:
        self._records = records

    @property
    def categories(self) -> OrmCategoryRepository:
        return self._categories

    @categories.setter
    def categories(self, categories: OrmCategoryRepository) -> None:
        self._categories = categories

    @property
    def database(self) -> OrmDatabaseRepository:
        return self._database

    @database.setter
    def database(self, database: OrmDatabaseRepository) -> None:
        self._database = database
