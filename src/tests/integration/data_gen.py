import random
import uuid
from datetime import datetime, timedelta
from typing import Optional

from configs.config import Settings
from domain.models import Resource, Visitor, Record, Category
from service.orm_uow import OrmUnitOfWork


def random_category() -> Category:
    return Category(name=random.choice(Settings().get_categories()))


def random_resource(category: Optional[Category] = None) -> Resource:
    category = category or random_category()
    return Resource(
        id=random.randint(1, 9999999),
        name=str(uuid.uuid4()),
        category_name=category.name,
        vendor_code=str(uuid.uuid4())
    )


def random_visitor() -> Visitor:
    return Visitor(
        id=random.randint(1, 9999999),
        email=f"{str(uuid.uuid4())}@skbkontur.ru",
        is_admin=False,
        full_name=str(uuid.uuid4()),
        username=str(uuid.uuid4())
    )


def random_take_record(
        visitor: Optional[Visitor] = None,
        resource: Optional[Resource] = None,
        take_date: Optional[datetime] = None,
        return_date: Optional[datetime] = None
) -> Record:
    visitor = visitor or random_visitor()
    resource = resource or random_resource()
    return Record(
        id=random.randint(1, 9999999),
        resource_id=resource.id,
        user_email=visitor.email,
        take_date=take_date or datetime.now() - timedelta(days=random.randint(1, 50)),
        return_date=return_date or datetime.now() + timedelta(days=random.randint(5, 50)),
        visitor=visitor,
        resource=resource
    )


def random_expiring_record(
        visitor: Visitor,
        resource: Resource,
        take_date: Optional[datetime] = None,
        expired_days_ago: int = 1
) -> Record:
    record = random_take_record(visitor, resource, take_date)
    record.return_date = datetime.now() - timedelta(days=expired_days_ago)
    return record


def random_finished_record(
        visitor: Visitor,
        resource: Resource,
        take_date: Optional[datetime] = None,
        return_date: Optional[datetime] = None
) -> Record:
    record = random_take_record(visitor, resource, take_date, return_date)
    record.finished = True
    return record


def random_queue_record(
        visitor: Visitor,
        resource: Resource,
        enqueue_date: Optional[datetime] = None
) -> Record:
    return Record(
        id=random.randint(1, 9999999),
        resource_id=resource.id,
        user_email=visitor.email,
        enqueue_date=enqueue_date or datetime.now() - timedelta(days=random.randint(1, 50)),
        visitor=visitor,
        resource=resource
    )


def added_category() -> Category:
    return random_category()


async def added_resource(category: Optional[Category] = None) -> Resource:
    category = category or added_category()
    resource = random_resource(category)
    async with OrmUnitOfWork() as uow:
        uow.resources.add(resource)
    return resource


async def added_visitor(visitor: Optional[Visitor] = None) -> Visitor:
    visitor = visitor or random_visitor()
    async with OrmUnitOfWork() as uow:
        uow.visitors.add(visitor)
    return visitor


async def added_take_record(visitor: Optional[Visitor] = None, resource: Optional[Resource] = None) -> Record:
    visitor = visitor or await added_visitor()
    resource = resource or await added_resource()
    record = random_take_record(visitor, resource)
    async with OrmUnitOfWork() as uow:
        uow.records.add(record)
    return record


async def added_queue_record(visitor: Optional[Visitor] = None, resource: Optional[Resource] = None) -> Record:
    visitor = visitor or await added_visitor()
    resource = resource or await added_resource()
    record = random_queue_record(visitor, resource)
    async with OrmUnitOfWork() as uow:
        uow.records.add(record)
    return record


async def added_finished_record(
        visitor: Optional[Visitor] = None,
        resource: Optional[Resource] = None,
        return_date: Optional[datetime] = None
) -> Record:
    visitor = visitor or await added_visitor()
    resource = resource or await added_resource()
    record = random_finished_record(visitor, resource, return_date=return_date)
    async with OrmUnitOfWork() as uow:
        uow.records.add(record)
    return record


async def added_expired_record(visitor: Optional[Visitor] = None, resource: Optional[Resource] = None) -> Record:
    visitor = visitor or await added_visitor()
    resource = resource or await added_resource()
    record = random_expiring_record(visitor, resource)
    async with OrmUnitOfWork() as uow:
        uow.records.add(record)
    return record


def random_str() -> str:
    return str(uuid.uuid4())


def random_email() -> str:
    return f"{random_str()}@skbkontur.ru"


def random_number() -> int:
    return random.randint(1, 9999999)
