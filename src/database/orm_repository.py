from abc import ABC
from datetime import datetime as dt, timedelta as td, time as time
from typing import Optional, List, Tuple

from sqlalchemy import select, delete, or_, text
from sqlalchemy.ext.asyncio import AsyncSession

from database.repository import ResourceRepository, VisitorRepository, RecordRepository, CategoryRepository, \
    DatabaseRepository
from database.repository_helpers import _prepare_filters_for_strings
from domain.models import Resource, Visitor, Record, Category, Base


class OrmResourceRepository(ResourceRepository, ABC):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, resource_id: int) -> Optional[Resource]:
        return await self.session.get(Resource, resource_id)

    async def get_by_vendor_code(self, vendor_code: str) -> Optional[Resource]:
        objects = await self.session.execute(select(Resource).filter(Resource.vendor_code == vendor_code))
        resources = objects.scalars().unique().all()
        return resources[0] if len(resources) != 0 else None

    async def list_by_category_name(self, category_name: str) -> List[Resource]:
        stmt = select(Resource).filter(Resource.category_name == category_name)
        await self.session.execute(stmt)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get_queue(self, resource_id: int) -> List[Record]:
        """Возвращает очередь на определенный ресурс"""
        resource = await self.session.get(Resource, resource_id)
        if resource is None:
            return []
        return list(resource.queue_records)

    async def get_take(self, resource_id: int) -> Optional[Record]:
        resource = await self.session.get(Resource, resource_id)
        if resource is None:
            return None
        return resource.take_record

    async def search_resource(self, search_key: str, limit: int, max_id: int) -> "List[Resource]":
        """
        Ищет ресурсы по запросу search_key: если это число меньше max_id - по id,
        иначе - по другим полям
        """
        if search_key.isnumeric() and int(search_key) < max_id:
            filters = [Resource.id.in_([int(search_key)])]
        else:
            filters = _prepare_filters_for_strings(
                model=Resource,
                fields=["name", "category_name", "vendor_code"],
                search_key=search_key
            )
        stmt = select(Resource).filter(or_(*filters)).limit(limit)
        result = await self.session.scalars(stmt)
        resources = result.all()
        return list(resources)

    def add(self, resource: Resource) -> None:
        self.session.add(resource)

    async def list(self) -> List[Resource]:
        result = await self.session.scalars(select(Resource))
        return list(result.unique())

    async def delete(self, resource_id: int) -> Optional[Resource]:
        resource = await self.session.get(Resource, resource_id)
        if not resource:
            return None
        await self.session.delete(resource)
        return resource

    async def delete_all(self, only_free_resources: bool) -> List[Resource]:
        stmt = select(Resource)
        if only_free_resources:
            stmt = stmt.filter(Resource.take_record == None)
        result = await self.session.scalars(stmt)
        resources = result.all()
        for resource in resources:
            await self.session.delete(resource)
        return resources


class OrmVisitorRepository(VisitorRepository, ABC):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, email: str) -> Optional[Visitor]:
        return await self.session.get(Visitor, email)

    async def get_by_id(self, visitor_id: int) -> Optional[Visitor]:
        objects = await self.session.execute(select(Visitor).filter(Visitor.id == visitor_id))
        visitors = objects.scalars().unique().all()
        return visitors[0] if len(visitors) != 0 else None

    async def get_by_chat_id(self, chat_id: int) -> "Optional[Visitor]":
        stmt = select(Visitor).filter_by(chat_id=chat_id)
        result = await self.session.scalars(stmt)
        users = result.all()
        return users[0] if len(users) != 0 else None

    async def get_taken_resources(self, visitor: Visitor) -> List[Resource]:
        visitor = await self.session.merge(visitor)
        return [i.resource for i in visitor.take_records]

    async def get_queue(self, visitor: Visitor) -> list[Resource]:
        visitor = await self.session.merge(visitor)
        return [i.resource for i in visitor.queue_records]

    async def search(self, search_key: str, limit: int) -> "List[Visitor]":
        filters = list()
        if search_key.isnumeric():
            filters.append(Visitor.id.in_([int(search_key)]))
            filters.append(Visitor.chat_id.in_([int(search_key)]))
        else:
            filters = _prepare_filters_for_strings(
                model=Visitor,
                fields=["email", "full_name", "username", "comment"],
                search_key=search_key
            )
        stmt = select(Visitor).filter(or_(*filters)).limit(limit)
        result = await self.session.scalars(stmt)
        resources = result.all()
        return list(resources)

    def add(self, visitor: Visitor) -> None:
        self.session.add(visitor)

    async def list(self) -> List[Visitor]:
        result = await self.session.scalars(select(Visitor))
        return list(result.unique())

    async def delete(self, email: str) -> Optional[Visitor]:
        visitor = await self.session.get(Visitor, email)
        if not visitor:
            return None
        await self.session.delete(visitor)
        return visitor


class OrmRecordRepository(RecordRepository, ABC):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, record_id: int) -> Optional[Record]:
        return await self.session.get(Record, record_id)

    async def get_take_record(self, resource_id: int, email: str) -> Optional[Record]:
        take_record = (await self.session.get(Resource, resource_id)).take_record
        return take_record if take_record.user_email == email else None

    async def get_queue_record(self, resource_id: int, email: str) -> Optional[Record]:
        queue_records = (await self.session.get(Resource, resource_id)).queue_records
        records = [i for i in queue_records if i.user_email == email]
        return records[0] if len(records) != 0 else None

    async def get_expiring(self, expire_after_days: int) -> List[Tuple[Record, int]]:
        """Возвращает записи, по которым пора уведомлять пользователей, и количество дней до просрочки"""
        return_date_to_start_notify = dt.combine(dt.now(), time.max) + td(days=expire_after_days)
        result = await self.session.execute(select(Record).filter(
            Record.return_date <= return_date_to_start_notify,
            Record.finished == False
        ))
        records: List[Record] = result.scalars().unique().all()
        return [(i, (dt.combine(i.return_date, time.max) - dt.now()).days) for i in records]

    def add(self, record: Record) -> None:
        self.session.add(record)

    async def put(self, record_id: int, address: str, return_date: dt) -> Optional[Record]:
        record = await self.session.get(Record, record_id)
        if not record:
            return None
        record.return_date = return_date
        record.address = address
        return record

    async def list(self) -> List[Record]:
        result = await self.session.scalars(select(Record))
        return list(result.unique())

    async def delete(self, record: Record) -> None:
        await self.session.delete(record)

    async def delete_finished(self, max_age: int = 100) -> None:
        stmt = delete(Record).filter(
            Record.finished == True,
            Record.return_date < dt.now() - td(days=max_age)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_all_taken(self) -> Tuple[List[Record], List[Resource]]:
        query = await self.session.execute(select(Record).filter(Record.take_date != None, Record.finished == False))
        records = list(query.scalars().unique().all())
        resources = [i.resource for i in records]
        return records, resources


class OrmCategoryRepository(CategoryRepository, ABC):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, name: str) -> Optional[Category]:
        return await self.session.get(Category, name)

    def add(self, category: Category) -> None:
        self.session.add(category)

    async def list(self) -> List[Category]:
        result = await self.session.scalars(select(Category))
        return list(result.unique())

    async def delete(self, category_name: str) -> Optional[Category]:
        category = await self.session.get(Category, category_name)
        if not category:
            return None
        await self.session.delete(category)
        return category


class OrmDatabaseRepository(DatabaseRepository, ABC):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def drop(self) -> None:
        connection = await self.session.connection()
        await connection.run_sync(Base.metadata.drop_all)

    async def start(self) -> None:
        connection = await self.session.connection()
        await connection.run_sync(Base.metadata.create_all)

    async def get_revisions(self) -> List[str]:
        result = await self.session.scalars(text("select * from alembic_version"))
        revisions = result.all()
        return [str(i) for i in revisions]
