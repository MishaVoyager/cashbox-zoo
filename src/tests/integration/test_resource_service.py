import random
from copy import copy
from datetime import datetime, timedelta

import pytest

import tests.integration.data_gen as data_gen
from database.uow import UnitOfWork
from domain.models import Category, Record
from service.services import ResourceService, CategoryService, RecordService


@pytest.mark.asyncio
async def test_delete_success(resource_service: ResourceService) -> None:
    resource = await data_gen.added_resource()
    delete_result = await resource_service.delete(resource.id)
    assert delete_result.is_success
    result = await resource_service.get(resource.id)
    assert result.is_failure


@pytest.mark.asyncio
async def test_delete_404(resource_service: ResourceService) -> None:
    resource = data_gen.random_resource()
    delete_result = await resource_service.delete(resource.id)
    assert delete_result.is_failure
    assert delete_result.error_code == 404


@pytest.mark.asyncio
async def test_get_success(resource_service: ResourceService) -> None:
    resource = await data_gen.added_resource()
    result = await resource_service.get(resource.id)
    assert result.unwrap().id == resource.id


@pytest.mark.asyncio
async def test_get_404(resource_service: ResourceService) -> None:
    resource = data_gen.random_resource()
    result = await resource_service.get(resource.id)
    assert result.is_failure
    assert result.error_code == 404


@pytest.mark.asyncio
async def test_get_by_vendor_code_success(resource_service: ResourceService) -> None:
    resource = await data_gen.added_resource()
    result = await resource_service.get_by_vendor_code(resource.vendor_code)
    assert result.unwrap().id == resource.id


@pytest.mark.asyncio
async def test_get_by_vendor_code_error(resource_service: ResourceService) -> None:
    resource = data_gen.random_resource()
    result = await resource_service.get_by_vendor_code(resource.vendor_code)
    assert result.is_failure
    assert result.error_code == 404


@pytest.mark.asyncio
async def test_get_all_success(resource_service: ResourceService) -> None:
    resource1 = await data_gen.added_resource()
    resource2 = await data_gen.added_resource()
    result = await resource_service.get_all()
    ids = [i.id for i in result.unwrap()]
    assert resource1.id in ids and resource2.id in ids


@pytest.mark.asyncio
async def test_get_all_empty_list(resource_service: ResourceService) -> None:
    result = await resource_service.get_all()
    assert result.is_success
    assert result.unwrap() == []


@pytest.mark.asyncio
async def test_search_success(resource_service: ResourceService) -> None:
    resource1 = await data_gen.added_resource()
    resource2 = await data_gen.added_resource()
    result = await resource_service.search(resource1.name[0:10], 200)
    ids = [i.id for i in result.unwrap()]
    assert resource1.id in ids
    assert resource2.id not in ids


@pytest.mark.asyncio
async def test_search_empty_list(resource_service: ResourceService) -> None:
    result = await resource_service.search(data_gen.random_str(), 200)
    assert result.is_success
    assert result.unwrap() == []


@pytest.mark.asyncio
async def test_list_by_category_name_success(resource_service: ResourceService,
                                             category_service: CategoryService) -> None:
    category = data_gen.random_category()
    resource1 = await data_gen.added_resource(category)
    resource2 = await data_gen.added_resource(category)
    new_category = Category(name=data_gen.random_str())
    await category_service.add(new_category)
    resource3 = await data_gen.added_resource(new_category)
    result = await resource_service.list_by_category_name(category.name)
    ids = [i.id for i in result.unwrap()]
    assert resource1.id in ids and resource2.id in ids and resource3.id not in ids


@pytest.mark.asyncio
async def test_list_by_category_name_unknown_category_404(resource_service: ResourceService,
                                                          category_service: CategoryService) -> None:
    random_category_name = data_gen.random_str()
    result = await resource_service.list_by_category_name(random_category_name)
    assert result.is_failure
    assert result.error_code == 404


@pytest.mark.asyncio
async def test_list_by_category_name_empty_list(
        resource_service: ResourceService,
        category_service: CategoryService) -> None:
    new_category = Category(name=data_gen.random_str())
    await category_service.add(new_category)
    result = await resource_service.list_by_category_name(new_category.name)
    assert result.is_success
    assert result.unwrap() == []


@pytest.mark.asyncio
async def test_get_categories_success(resource_service: ResourceService, category_service: CategoryService) -> None:
    category = data_gen.random_category()
    await data_gen.added_resource(category)
    new_category = Category(name="new")
    await category_service.add(new_category)
    category_without_resources = Category(name="some")
    await category_service.add(category_without_resources)
    await data_gen.added_resource(new_category)
    result = await resource_service.get_categories()
    names = [i for i in result.unwrap()]
    assert set(names) == {category.name, new_category.name}


@pytest.mark.asyncio
async def test_get_categories_empty_list(resource_service: ResourceService, category_service: CategoryService) -> None:
    result = await resource_service.get_categories()
    assert result.is_success
    assert result.unwrap() == []


@pytest.mark.asyncio
async def test_get_finished_records_success(resource_service: ResourceService) -> None:
    original_finished_record = await data_gen.added_finished_record()
    result = await resource_service.get_finished_records(original_finished_record.resource_id)
    finished_record = result.unwrap()[0]
    assert finished_record.return_date == original_finished_record.return_date


@pytest.mark.asyncio
async def test_get_finished_records_404(resource_service: ResourceService) -> None:
    result = await resource_service.get_finished_records(data_gen.random_number())
    assert result.is_failure
    assert result.error_code == 404


@pytest.mark.asyncio
async def test_get_finished_records_empty_list(resource_service: ResourceService) -> None:
    resource = await data_gen.added_resource()
    result = await resource_service.get_finished_records(resource.id)
    assert result.is_success
    assert result.unwrap() == []


@pytest.mark.asyncio
async def test_get_take_record_success(resource_service: ResourceService) -> None:
    take_record = await data_gen.added_take_record()
    result = await resource_service.get_take_record(take_record.resource_id)
    assert result.unwrap().id == take_record.id


@pytest.mark.asyncio
async def test_get_take_record_404(resource_service: ResourceService) -> None:
    result = await resource_service.get_take_record(data_gen.random_number())
    assert result.is_failure
    assert result.error_code == 404


@pytest.mark.asyncio
async def test_get_take_record_no_record(resource_service: ResourceService) -> None:
    resource = await data_gen.added_resource()
    result = await resource_service.get_take_record(resource.id)
    assert result.is_success
    assert result.unwrap() is None


@pytest.mark.asyncio
async def test_get_queue_records_success(resource_service: ResourceService) -> None:
    resource = await data_gen.added_resource()
    queue_record1 = await data_gen.added_queue_record(resource=resource)
    queue_record2 = await data_gen.added_queue_record(resource=resource)
    another_queue_record = await data_gen.added_queue_record()
    result = await resource_service.get_queue_records(resource.id)
    ids = [i.id for i in result.unwrap()]
    assert set(ids) == {queue_record1.id, queue_record2.id}
    assert another_queue_record.id not in ids


@pytest.mark.asyncio
async def test_get_queue_records_404(resource_service: ResourceService) -> None:
    result = await resource_service.get_queue_records(data_gen.random_number())
    assert result.is_failure
    assert result.error_code == 404


@pytest.mark.asyncio
async def test_get_queue_records_empty_list(resource_service: ResourceService) -> None:
    resource = await data_gen.added_resource()
    result = await resource_service.get_queue_records(resource.id)
    assert result.unwrap() == []


@pytest.mark.asyncio
async def test_delete_all_free_success(resource_service: ResourceService) -> None:
    take_record = await data_gen.added_take_record()
    free_resource = await data_gen.added_resource()
    result = await resource_service.delete_all_free()
    deleted_resources = result.unwrap()
    assert len(deleted_resources) == 1
    assert deleted_resources[0].id == free_resource.id
    get_taken_result = await resource_service.get(take_record.resource_id)
    assert get_taken_result.unwrap().id == take_record.resource_id


@pytest.mark.asyncio
async def test_delete_all_free_empty_list(resource_service: ResourceService) -> None:
    result = await resource_service.delete_all_free()
    assert result.unwrap() == []


@pytest.mark.asyncio
async def test_delete_all_free_only_taken(resource_service: ResourceService) -> None:
    await data_gen.added_take_record()
    result = await resource_service.delete_all_free()
    assert result.unwrap() == []


@pytest.mark.asyncio
async def test_update_field_success(resource_service: ResourceService) -> None:
    resource = await data_gen.added_resource()
    await resource_service.update_field(resource.id, "name", "qwerty")
    result = await resource_service.get(resource.id)
    assert result.unwrap().name == "qwerty"


@pytest.mark.asyncio
async def test_update_field_404(resource_service: ResourceService) -> None:
    result = await resource_service.update_field(data_gen.random_number(), "name", "qwerty")
    assert result.is_failure
    assert result.error_code == 404


@pytest.mark.asyncio
async def test_update_field_wrong_field_name_400(resource_service: ResourceService) -> None:
    resource = await data_gen.added_resource()
    result = await resource_service.update_field(
        resource_id=resource.id,
        field_name=data_gen.random_str(),
        value="qwerty")
    assert result.is_failure
    assert result.error_code == 400


@pytest.mark.asyncio
async def test_add_with_record_success(
        resource_service: ResourceService,
        uow: UnitOfWork
) -> None:
    resource = data_gen.random_resource()
    take_record = await data_gen.added_take_record(resource=resource)
    await resource_service.add_with_record(resource, take_record)
    result = await resource_service.get(resource.id)
    resource_info = result.unwrap()
    assert resource_info.id == resource.id
    assert resource_info.return_date == take_record.return_date


@pytest.mark.asyncio
async def test_add_with_record_new_visitor_success(
        resource_service: ResourceService,
        uow: UnitOfWork
) -> None:
    resource = data_gen.random_resource()
    visitor = data_gen.random_visitor()
    take_record = Record(
        id=random.randint(1, 9999999),
        resource_id=resource.id,
        user_email=visitor.email,
        take_date=datetime.now() - timedelta(days=random.randint(1, 50)),
        return_date=datetime.now() + timedelta(days=random.randint(1, 50)),
    )
    await resource_service.add_with_record(resource, take_record)
    result = await resource_service.get(resource.id)
    resource_info = result.unwrap()
    assert resource_info.id == resource.id
    assert resource_info.take_date == take_record.take_date
    async with uow:
        added_visitor = await uow.visitors.get(visitor.email)
    assert added_visitor.email == visitor.email


@pytest.mark.asyncio
async def test_add_with_record_empty_record_success(resource_service: ResourceService) -> None:
    resource = data_gen.random_resource()
    await resource_service.add_with_record(resource, None)
    result = await resource_service.get(resource.id)
    assert result.unwrap().id == resource.id


@pytest.mark.asyncio
async def test_add_with_record_existed_resource_409(resource_service: ResourceService) -> None:
    resource = await data_gen.added_resource()
    result = await resource_service.add_with_record(resource, None)
    assert result.is_failure
    assert result.error_code == 409


@pytest.mark.asyncio
async def test_add_with_record_resource_ids_not_match_417(resource_service: ResourceService) -> None:
    resource = data_gen.random_resource()
    new_take_record = data_gen.random_take_record()
    result = await resource_service.add_with_record(resource, new_take_record)
    assert result.is_failure
    assert result.error_code == 417


@pytest.mark.asyncio
async def test_add_many_with_record_success(resource_service: ResourceService, record_service: RecordService) -> None:
    resource_with_record = data_gen.random_resource()
    take_record = data_gen.random_take_record(resource=resource_with_record)
    resource_without_record = data_gen.random_resource()
    to_add = [(resource_with_record, take_record), (resource_without_record, None)]
    add_result = await resource_service.add_many_with_record(to_add)
    assert add_result.is_success
    assert (await resource_service.get(resource_without_record.id)).is_success
    assert (await resource_service.get(resource_with_record.id)).is_success
    record = (await record_service.get(take_record.id)).unwrap()
    assert record.resource_id == resource_with_record.id


@pytest.mark.asyncio
async def test_add_many_with_record_409(resource_service: ResourceService, record_service: RecordService) -> None:
    resource = await data_gen.added_resource()
    to_add = [(data_gen.random_resource(), None), (resource, None)]
    add_result = await resource_service.add_many_with_record(to_add)
    assert add_result.is_failure
    assert add_result.error_code == 409


@pytest.mark.asyncio
async def test_add_many_with_record_417(resource_service: ResourceService, record_service: RecordService) -> None:
    to_add = [(data_gen.random_resource(), None), (data_gen.random_resource(), data_gen.random_take_record())]
    add_result = await resource_service.add_many_with_record(to_add)
    assert add_result.is_failure
    assert add_result.error_code == 417


@pytest.mark.asyncio
async def test_add_many_with_record_id_duplicates_400(
        resource_service: ResourceService,
        record_service: RecordService) -> None:
    resource = data_gen.random_resource()
    second_resource = copy(resource)
    second_resource.vendor_code = data_gen.random_str()
    to_add = [(resource, None), (second_resource, None)]
    add_result = await resource_service.add_many_with_record(to_add)
    assert add_result.is_failure
    assert add_result.error_code == 400
    assert str(resource.id) in add_result.error


@pytest.mark.asyncio
async def test_add_many_with_record_vendor_code_duplicates_400(
        resource_service: ResourceService,
        record_service: RecordService) -> None:
    resource = data_gen.random_resource()
    second_resource = copy(resource)
    second_resource.id = data_gen.random_number()
    to_add = [(resource, None), (second_resource, None)]
    add_result = await resource_service.add_many_with_record(to_add)
    assert add_result.is_failure
    assert add_result.error_code == 400
    assert resource.vendor_code in add_result.error
