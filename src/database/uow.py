from abc import ABC, abstractmethod
from typing import Any

from database.repository import ResourceRepository, VisitorRepository, RecordRepository, CategoryRepository, \
    DatabaseRepository


class UnitOfWork(ABC):

    async def __aenter__(self) -> 'UnitOfWork':
        raise NotImplemented

    async def __aexit__(self, *args) -> None:
        raise NotImplemented

    @abstractmethod
    async def commit(self) -> None:
        raise NotImplemented

    @abstractmethod
    async def rollback(self) -> None:
        raise NotImplemented

    @abstractmethod
    async def merge(self, object: Any) -> Any:
        raise NotImplemented

    @property
    @abstractmethod
    def resources(self) -> ResourceRepository:
        raise NotImplemented

    @resources.setter
    @abstractmethod
    def resources(self, resources: ResourceRepository) -> None:
        pass

    @property
    @abstractmethod
    def visitors(self) -> VisitorRepository:
        raise NotImplemented

    @visitors.setter
    @abstractmethod
    def visitors(self, visitors: VisitorRepository) -> None:
        pass

    @property
    @abstractmethod
    def records(self) -> RecordRepository:
        raise NotImplemented

    @records.setter
    @abstractmethod
    def records(self, records: RecordRepository) -> None:
        pass

    @property
    @abstractmethod
    def categories(self) -> CategoryRepository:
        raise NotImplemented

    @categories.setter
    @abstractmethod
    def categories(self, categories: CategoryRepository) -> None:
        pass

    @property
    @abstractmethod
    def database(self) -> DatabaseRepository:
        raise NotImplemented

    @database.setter
    @abstractmethod
    def database(self, database: DatabaseRepository) -> None:
        pass
