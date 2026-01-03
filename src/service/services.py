import logging
from collections import Counter
from datetime import datetime as dt
from typing import Optional, List, Any, Tuple

from configs.config import Settings
from database.uow import UnitOfWork
from domain.converters import convert_resource_to_dto
from domain.expiring_records_dto import ExpiringRecordsDTO
from domain.models import Visitor, Resource, Record, ActionType, Category
from domain.resource_info import ResourceInfoDTO
from domain.return_resource_dto import ReturnResourceDto
from domain.visitor_info_dto import VisitorInfoDTO
from service.service_result import ServiceResult


class VisitorService:
    def __init__(self, unit_of_work: UnitOfWork):
        self.unit_of_work = unit_of_work

    async def add_visitor(self, visitor: Visitor) -> ServiceResult[Visitor]:
        async with self.unit_of_work as uow:
            existed_visitor = await uow.visitors.get(visitor.email)
            if existed_visitor:
                return ServiceResult.failure(f"Visitor with email {visitor.email} already exists", 409)
            uow.visitors.add(visitor)
        return ServiceResult.success(visitor)

    async def get(self, email: str) -> ServiceResult[Visitor]:
        async with self.unit_of_work as uow:
            visitor = await uow.visitors.get(email)
        if visitor is None:
            return ServiceResult.failure(f"Visitor with email {email} not found", 404)
        return ServiceResult.success(visitor)

    async def get_by_chat_id(self, chat_id: int) -> ServiceResult[Visitor]:
        async with self.unit_of_work as uow:
            visitor = await uow.visitors.get_by_chat_id(chat_id)
        if visitor is None:
            return ServiceResult.failure(f"Visitor with chat_id {chat_id} not found", 404)
        return ServiceResult.success(visitor)

    async def get_by_id(self, visitor_id: int) -> ServiceResult[Visitor]:
        async with self.unit_of_work as uow:
            visitor = await uow.visitors.get_by_id(visitor_id)
        if visitor is None:
            return ServiceResult.failure(f"Visitor with id {visitor_id} not found", 404)
        return ServiceResult.success(visitor)

    async def get_all(self) -> ServiceResult[List[Visitor]]:
        async with self.unit_of_work as uow:
            visitor = await uow.visitors.list()
        return ServiceResult.success(visitor)

    async def get_finished_records(self, visitor_id: int) -> ServiceResult[List[VisitorInfoDTO]]:
        result = []
        async with self.unit_of_work as uow:
            visitor = await uow.visitors.get_by_id(visitor_id)
            finished_records: List[Record] = visitor.finished_records
            for record in finished_records:
                visitor_info = VisitorInfoDTO(
                    visitor_id=visitor.id,
                    visitor_email=visitor.email,
                    visitor_name=visitor.full_name,
                    visitor_username=visitor.username,
                    resource_name=record.resource.name,
                    resource_id=record.resource.id,
                    record_id=record.id,
                    take_date=record.take_date,
                    return_date=record.return_date,
                    enqueue_date=record.enqueue_date,
                    finished=record.finished,
                    address=record.address
                )
                result.append(visitor_info)
        return ServiceResult.success(result)

    async def get_taken_resources(self, visitor: Visitor) -> ServiceResult[List[ResourceInfoDTO]]:
        """Возвращает список ресурсов, которыми владеет пользователь"""
        async with self.unit_of_work as uow:
            existed_visitor = await uow.visitors.get(visitor.email)
            if not existed_visitor:
                return ServiceResult.failure(f"Visitor with email {visitor.email} not found", 404)
            resources = await uow.visitors.get_taken_resources(visitor)
        async with self.unit_of_work as uow:
            result = []
            for i in resources:
                resource = await uow.merge(i)
                result.append(convert_resource_to_dto(resource, resource.take_record))
        return ServiceResult.success(result)

    async def get_queue(self, visitor: Visitor) -> ServiceResult[List[ResourceInfoDTO]]:
        async with self.unit_of_work as uow:
            existed_visitor = await uow.visitors.get(visitor.email)
            if not existed_visitor:
                return ServiceResult.failure(f"Visitor with email {visitor.email} not found", 404)
            resources = await uow.visitors.get_queue(visitor)
        async with self.unit_of_work as uow:
            result = []
            for i in resources:
                resource = await uow.merge(i)
                result.append(convert_resource_to_dto(resource, resource.take_record))
        return ServiceResult.success(result)

    async def auth(self, new_visitor: Visitor) -> ServiceResult[Visitor]:
        """Добавляет или обновляет пользователя при первом входе в систему"""
        async with self.unit_of_work as uow:
            existed_visitor = await uow.visitors.get(new_visitor.email)
            is_admin = new_visitor.email in Settings().admins.split()
            if existed_visitor:
                existed_visitor.chat_id = new_visitor.chat_id
                existed_visitor.user_id = new_visitor.user_id
                existed_visitor.username = new_visitor.username
                existed_visitor.full_name = new_visitor.full_name
                existed_visitor.is_admin = is_admin
                return ServiceResult.success(existed_visitor)
            else:
                new_visitor.is_admin = is_admin
                uow.visitors.add(new_visitor)
                logging.info(f"Пользователь авторизовался: {repr(new_visitor)}")
                return ServiceResult.success(new_visitor)

    async def add_without_auth(self, email: str) -> ServiceResult[Visitor]:
        async with self.unit_of_work as uow:
            if await uow.visitors.get(email):
                return ServiceResult.failure(f"Visitor with email {email} already exists", 409)
            visitor = Visitor(email=email)
            uow.visitors.add(visitor)
        return ServiceResult.success(visitor)

    async def update(self, visitor_id: int, email: Optional[str] = None, comment: Optional[str] = None) -> \
            ServiceResult[Visitor]:
        async with self.unit_of_work as uow:
            visitor = await uow.visitors.get_by_id(visitor_id)
            if not visitor:
                return ServiceResult.failure(f"Visitor with id {visitor_id} not found", 404)
            if email is not None:
                visitor.email = email
            if comment is not None:
                visitor.comment = comment
        return ServiceResult.success(visitor)

    async def delete(self, email: str) -> ServiceResult[Visitor]:
        async with self.unit_of_work as uow:
            visitor = await uow.visitors.delete(email)
        if visitor is None:
            return ServiceResult.failure(f"Visitor with email {email} not found", 404)
        return ServiceResult.success(visitor)

    async def search(self, search_key: str) -> ServiceResult[List[Visitor]]:
        async with self.unit_of_work as uow:
            visitors = await uow.visitors.search(search_key, 200)
        return ServiceResult.success(visitors)


class ResourceService:
    def __init__(self, unit_of_work: UnitOfWork):
        self.unit_of_work = unit_of_work

    async def get(self, resource_id: int) -> ServiceResult[ResourceInfoDTO]:
        async with self.unit_of_work as uow:
            resource = await uow.resources.get(resource_id)
            if resource is None:
                return ServiceResult.failure(f"Resource with id {resource_id} not found", 404)
            result = convert_resource_to_dto(resource, resource.take_record)
        return ServiceResult.success(result)

    async def get_by_vendor_code(self, vendor_code: str) -> ServiceResult[ResourceInfoDTO]:
        async with self.unit_of_work as uow:
            resource = await uow.resources.get_by_vendor_code(vendor_code)
            if resource is None:
                return ServiceResult.failure(f"Resource with vendor_code {vendor_code} not found", 404)
            result = convert_resource_to_dto(resource, resource.take_record)
        return ServiceResult.success(result)

    async def list_by_category_name(self, category_name: str) -> ServiceResult[List[ResourceInfoDTO]]:
        async with self.unit_of_work as uow:
            category = await uow.categories.get(category_name)
            if category is None:
                return ServiceResult.failure(f"Category with name {category_name} not found", 404)
            resources = await uow.resources.list_by_category_name(category_name)
            result = [convert_resource_to_dto(i, i.take_record) for i in resources]
        return ServiceResult.success(result)

    async def get_categories(self) -> ServiceResult[List[str]]:
        async with self.unit_of_work as uow:
            resources = await uow.resources.list()
        categories = list(set([i.category_name for i in resources]))
        return ServiceResult.success(categories)

    async def get_finished_records(self, resource_id: int) -> ServiceResult[List[ResourceInfoDTO]]:
        async with self.unit_of_work as uow:
            resource = await uow.resources.get(resource_id)
            if resource is None:
                return ServiceResult.failure(f"Resource with id {resource_id} not found", 404)
            finished_records: List[Record] = resource.finished_records
        result = [convert_resource_to_dto(resource, i) for i in finished_records]
        return ServiceResult.success(result)

    async def get_take_record(self, resource_id: int) -> ServiceResult[Record]:
        async with self.unit_of_work as uow:
            resource = await uow.resources.get(resource_id)
            if resource is None:
                return ServiceResult.failure(f"Resource with id {resource_id} not found", 404)
        return ServiceResult.success(resource.take_record)

    async def get_queue_records(self, resource_id: int) -> ServiceResult[List[Record]]:
        async with self.unit_of_work as uow:
            resource = await uow.resources.get(resource_id)
            if resource is None:
                return ServiceResult.failure(f"Resource with id {resource_id} not found", 404)
            return ServiceResult.success(resource.queue_records)

    async def get_all(self) -> ServiceResult[List[ResourceInfoDTO]]:
        async with self.unit_of_work as uow:
            resources = await uow.resources.list()
            dtos = [convert_resource_to_dto(i, i.take_record) for i in resources]
        return ServiceResult(dtos)

    async def delete_all_free(self) -> ServiceResult[List[Resource]]:
        async with self.unit_of_work as uow:
            resources = await uow.resources.delete_all(only_free_resources=True)
        return ServiceResult.success(resources)

    async def update_field(self, resource_id: int, field_name: str, value: Any) -> ServiceResult[Resource]:
        async with self.unit_of_work as uow:
            resource = await uow.resources.get(resource_id)
            if resource is None:
                return ServiceResult.failure(f"Resource with id {resource_id} not found", 404)
            if field_name not in Resource.get_fields_names():
                return ServiceResult.failure(f"Resource does not have this field_name: {field_name}", 400)
            setattr(resource, field_name, value)
        return ServiceResult.success(resource)

    async def add_with_record(self, resource: Resource, take_record: Optional[Record]) -> ServiceResult:
        async with self.unit_of_work as uow:
            existed_resource = await uow.resources.get(resource.id)
            if existed_resource:
                return ServiceResult.failure(f"Resource with id {resource.id} already exists", 409)
            uow.resources.add(resource)
            if take_record and take_record.user_email:
                if take_record.resource_id != resource.id:
                    return ServiceResult.failure(
                        f"Record has resource_id {take_record.resource_id}, but resource has {resource.id}",
                        417
                    )
                visitor = await uow.visitors.get(take_record.user_email)
                if not visitor:
                    new_visitor = Visitor(email=take_record.user_email)
                    uow.visitors.add(new_visitor)
                uow.records.add(take_record)
            return ServiceResult()

    async def _check_duplicated(self,
                                resources_and_take_records: List[Tuple[Resource, Optional[Record]]]) -> ServiceResult:
        counts = Counter([i[0].id for i in resources_and_take_records])
        id_duplicates = [i for i, count in counts.items() if count > 1]
        counts = Counter([i[0].vendor_code for i in resources_and_take_records])
        vendor_code_duplicates = [i for i, count in counts.items() if count > 1]
        if len(id_duplicates) != 0:
            return ServiceResult.failure(f"Duplicated resource_ids: {' ,'.join([str(i) for i in id_duplicates])}", 400)
        if len(vendor_code_duplicates) != 0:
            return ServiceResult.failure(
                f"Duplicated vendor_codes: {' ,'.join([str(i) for i in vendor_code_duplicates])}", 400)
        return ServiceResult()

    async def add_many_with_record(
            self,
            resources_and_take_records: List[Tuple[Resource, Optional[Record]]]) -> ServiceResult:
        result = await self._check_duplicated(resources_and_take_records)
        if result.is_failure:
            return result
        async with self.unit_of_work as uow:
            for resource, take_record in resources_and_take_records:
                existed_resource = await uow.resources.get(resource.id)
                if existed_resource:
                    return ServiceResult.failure(f"Resource with id {resource.id} already exists", 409)
                uow.resources.add(resource)
                if take_record and take_record.user_email:
                    if take_record.resource_id != resource.id:
                        return ServiceResult.failure(
                            f"Record has resource_id {take_record.resource_id}, but resource has {resource.id}",
                            417
                        )
                    visitor = await uow.visitors.get(take_record.user_email)
                    if not visitor:
                        new_visitor = Visitor(email=take_record.user_email)
                        uow.visitors.add(new_visitor)
                    uow.records.add(take_record)
        return ServiceResult()

    async def search(self, search_key: str, limit: int, max_id: int = 10000) -> ServiceResult[List[ResourceInfoDTO]]:
        async with self.unit_of_work as uow:
            resources = await uow.resources.search_resource(search_key, limit, max_id)
            result = [convert_resource_to_dto(i, i.take_record) for i in resources]
        return ServiceResult.success(result)

    async def delete(self, resource_id: int) -> ServiceResult[Resource]:
        async with self.unit_of_work as uow:
            resource = await uow.resources.delete(resource_id)
        if resource is None:
            return ServiceResult.failure(f"Resource with id {resource_id} not found", 404)
        return ServiceResult.success(resource)


class RecordService:
    def __init__(self, unit_of_work: UnitOfWork):
        self.unit_of_work = unit_of_work

    async def get(self, record_id: int) -> ServiceResult[Record]:
        async with self.unit_of_work as uow:
            record = await uow.records.get(record_id)
        if record is None:
            return ServiceResult.failure(f"Record with id {record_id} not found", 404)
        else:
            return ServiceResult.success(record)

    async def get_all_taken(self) -> ServiceResult[List[ResourceInfoDTO]]:
        async with self.unit_of_work as uow:
            records, resources = await uow.records.get_all_taken()
            result = []
            for record, resource in zip(records, resources):
                result.append(convert_resource_to_dto(resource, record))
        return ServiceResult.success(result)

    async def get_expiring(self, expire_after_days: int) -> ServiceResult[List[ExpiringRecordsDTO]]:
        async with self.unit_of_work as uow:
            expiring_records_with_days = await uow.records.get_expiring(expire_after_days)
        result = []
        for record, days_before_expire in expiring_records_with_days:
            dto = ExpiringRecordsDTO(record=record, days_before_expire=days_before_expire)
            result.append(dto)
        return ServiceResult.success(result)

    async def _check_exists(self, resource_id: int, email: str) -> ServiceResult:
        async with self.unit_of_work as uow:
            resource = await uow.resources.get(resource_id)
            visitor = await uow.visitors.get(email)
        if resource is None:
            return ServiceResult.failure(f"Resource with id {resource_id} not found", 404)
        if visitor is None:
            return ServiceResult.failure(f"Visitor with email {email} not found", 404)
        return ServiceResult()

    async def enqueue(self, resource_id: int, email: str) -> ServiceResult[Record]:
        check_result = await self._check_exists(resource_id, email)
        if check_result.is_failure:
            return check_result
        async with self.unit_of_work as uow:
            queue_records = await uow.resources.get_queue(resource_id)
            if email in [i.visitor.email for i in queue_records]:
                return ServiceResult.failure("Visitor already in queue", 409)
            record = Record(resource_id=resource_id, user_email=email, enqueue_date=dt.now())
            uow.records.add(record)
        return ServiceResult.success(record)

    async def get_available_action(self, resource_id: int, email: str) -> ServiceResult[ActionType]:
        # А если есть очередь, но ресурс не занят - это парадокс
        check_result = await self._check_exists(resource_id, email)
        if check_result.is_failure:
            return check_result
        async with self.unit_of_work as uow:
            resource = await uow.resources.get(resource_id)
            resource_is_free = not resource.take_record
            visitor_has_it = resource.take_record and resource.take_record.user_email == email
            visitor_in_queue_for_it = email in [i.visitor.email for i in resource.queue_records]
        if resource_is_free:
            return ServiceResult.success(ActionType.TAKE)
        elif visitor_has_it:
            return ServiceResult.success(ActionType.RETURN)
        elif visitor_in_queue_for_it:
            return ServiceResult.success(ActionType.LEAVE)
        else:
            return ServiceResult.success(ActionType.QUEUE)

    async def delete_old_finished_records(self, max_age: int = 100) -> ServiceResult:
        async with self.unit_of_work as uow:
            await uow.records.delete_finished(max_age)
        return ServiceResult()

    async def leave_queue(self, resource_id: int, email: str) -> ServiceResult[Record]:
        check_result = await self._check_exists(resource_id, email)
        if check_result.is_failure:
            return check_result
        async with self.unit_of_work as uow:
            queue_record = await uow.records.get_queue_record(resource_id, email)
            if queue_record is None:
                return ServiceResult.failure(f"Record for resource_id {resource_id} and email {email} not found", 404)
            await uow.records.delete(queue_record)
        return ServiceResult.success(queue_record)

    async def take_resource(
            self,
            resource_id: int,
            user_email: str,
            address: Optional[str] = None,
            return_date: Optional[dt] = None
    ) -> ServiceResult[ResourceInfoDTO]:
        async with self.unit_of_work as uow:
            resource = await uow.resources.get(resource_id)
            if resource is None:
                return ServiceResult.failure(f"Resource with id {resource_id} not found", 404)
            visitor = await uow.visitors.get(user_email)
            if visitor is None:
                return ServiceResult.failure(f"Visitor with email {user_email} not found", 404)
            if resource.take_record:
                return ServiceResult.failure(f"Take record for resource with id {resource_id} already exists", 409)
            record = Record(
                resource_id=resource_id,
                user_email=user_email,
                take_date=dt.now(),
                return_date=return_date,
                address=address
            )
            uow.records.add(record)
        dto = convert_resource_to_dto(resource, record)
        return ServiceResult.success(dto)

    async def return_resource(self, resource_id: int) -> ServiceResult[ReturnResourceDto]:
        """Снимает ресурс с текущего пользователя и передает следующему"""
        async with self.unit_of_work as uow:
            take_record = await uow.resources.get_take(resource_id)
            if take_record is None:
                return ServiceResult.failure(f"No take_record for resource with id {resource_id}", 417)
            take_record.return_date = dt.now()
            take_record.finished = True
            return_resource_dto = ReturnResourceDto(
                resource=take_record.resource,
                previous_visitor_email=take_record.user_email
            )
            queue_records = await uow.resources.get_queue(resource_id)
            if len(queue_records) == 0:
                return ServiceResult.success(return_resource_dto)
            first_in_queue_record = queue_records[0]
            first_in_queue_record.enqueue_date = None
            first_in_queue_record.take_date = dt.now()
            return_resource_dto.new_visitor_email = first_in_queue_record.user_email
            return ServiceResult.success(return_resource_dto)

    async def put(self, record_id: int, address: str, return_date: dt) -> ServiceResult[ResourceInfoDTO]:
        """Снимает ресурс с текущего пользователя и передает следующему"""
        async with self.unit_of_work as uow:
            existed_record = await uow.records.get(record_id)
            if existed_record is None:
                return ServiceResult.failure(f"Record with id {record_id} not found", 404)
            record = await uow.records.put(record_id, address, return_date)
            result = convert_resource_to_dto(record.resource, record)
        return ServiceResult.success(result)


class CategoryService:
    def __init__(self, unit_of_work: UnitOfWork):
        self.unit_of_work = unit_of_work

    async def add(self, category: Category) -> ServiceResult:
        async with self.unit_of_work as uow:
            existed_category = await uow.categories.get(category.name)
            if existed_category:
                return ServiceResult.failure(f"Category with name {category.name} alreasy exists", 409)
            uow.categories.add(category)
        return ServiceResult()

    async def get(self, name: str) -> ServiceResult[Category]:
        async with self.unit_of_work as uow:
            category = await uow.categories.get(name)
            if category is None:
                return ServiceResult.failure(f"No category with name {name}", 404)
            else:
                return ServiceResult.success(category)

    async def delete(self, category_name: str) -> ServiceResult:
        async with self.unit_of_work as uow:
            category = await uow.categories.delete(category_name)
            if category is None:
                return ServiceResult.failure(f"No category with name {category_name}", 404)
        return ServiceResult.success(category)

    async def get_all(self) -> ServiceResult[List[Category]]:
        async with self.unit_of_work as uow:
            categories = await uow.categories.list()
        return ServiceResult.success(categories)
