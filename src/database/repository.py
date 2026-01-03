from abc import ABC, abstractmethod
from datetime import datetime as dt
from typing import List, Optional, Tuple

from domain.models import Resource, Visitor, Record, Category


class ResourceRepository(ABC):
    @abstractmethod
    async def get(self, resource_id: int) -> Optional[Resource]:
        raise NotImplemented

    @abstractmethod
    async def get_by_vendor_code(self, vendor_code: str) -> Optional[Resource]:
        raise NotImplemented

    @abstractmethod
    async def list_by_category_name(self, category_name: str) -> List[Resource]:
        raise NotImplemented

    @abstractmethod
    async def get_queue(self, resource_id: int) -> List[Record]:
        raise NotImplemented

    @abstractmethod
    async def get_take(self, resource_id: int) -> Optional[Record]:
        raise NotImplemented

    @abstractmethod
    async def search_resource(self, search_key: str, limit: int, max_id: int) -> "List[Resource]":
        raise NotImplemented

    @abstractmethod
    def add(self, resource: Resource) -> None:
        raise NotImplemented

    @abstractmethod
    async def list(self) -> List[Resource]:
        raise NotImplemented

    @abstractmethod
    async def delete(self, resource_id: int) -> Optional[Resource]:
        raise NotImplemented

    @abstractmethod
    async def delete_all(self, only_free_resources: bool) -> List[Resource]:
        raise NotImplemented


class VisitorRepository(ABC):
    @abstractmethod
    async def get(self, email: str) -> Optional[Visitor]:
        raise NotImplemented

    @abstractmethod
    async def get_by_id(self, visitor_id: int) -> Optional[Visitor]:
        raise NotImplemented

    @abstractmethod
    async def get_by_chat_id(self, chat_id: int) -> "Optional[Visitor]":
        raise NotImplemented

    @abstractmethod
    async def get_taken_resources(self, visitor: Visitor) -> List[Resource]:
        raise NotImplemented

    @abstractmethod
    async def get_queue(self, visitor: Visitor) -> list[Resource]:
        raise NotImplemented

    @abstractmethod
    async def search(self, search_key: str, limit: int) -> "List[Visitor]":
        raise NotImplemented

    @abstractmethod
    def add(self, visitor: Visitor) -> None:
        raise NotImplemented

    @abstractmethod
    async def list(self) -> List[Visitor]:
        raise NotImplemented

    @abstractmethod
    async def delete(self, email: str) -> Optional[Visitor]:
        raise NotImplemented


class RecordRepository(ABC):
    @abstractmethod
    async def get(self, record_id: int) -> Optional[Record]:
        raise NotImplemented

    @abstractmethod
    async def get_take_record(self, resource_id: int, email: str) -> Optional[Record]:
        raise NotImplemented

    @abstractmethod
    async def get_queue_record(self, resource_id: int, email: str) -> Optional[Record]:
        raise NotImplemented

    @abstractmethod
    async def get_expiring(self, expire_after_days: int) -> List[Tuple[Record, int]]:
        raise NotImplemented

    @abstractmethod
    def add(self, record: Record) -> None:
        raise NotImplemented

    async def put(self, record_id: int, address: str, return_date: dt) -> Optional[Record]:
        raise NotImplemented

    @abstractmethod
    async def list(self) -> List[Record]:
        raise NotImplemented

    @abstractmethod
    async def delete(self, record: Record) -> None:
        raise NotImplemented

    @abstractmethod
    async def delete_finished(self, max_age: int = 100) -> None:
        raise NotImplemented

    @abstractmethod
    async def get_all_taken(self) -> Tuple[List[Record], List[Resource]]:
        raise NotImplemented


class CategoryRepository(ABC):
    @abstractmethod
    async def get(self, name: str) -> Optional[Category]:
        raise NotImplemented

    @abstractmethod
    def add(self, category: Category) -> None:
        raise NotImplemented

    @abstractmethod
    async def list(self) -> List[Category]:
        raise NotImplemented

    @abstractmethod
    async def delete(self, category_name: str) -> Optional[Category]:
        raise NotImplemented


class DatabaseRepository(ABC):
    @abstractmethod
    async def drop(self) -> None:
        raise NotImplemented

    @abstractmethod
    async def start(self) -> None:
        raise NotImplemented

    @abstractmethod
    async def get_revisions(self) -> List[str]:
        raise NotImplemented
