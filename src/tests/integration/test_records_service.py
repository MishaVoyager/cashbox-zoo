import datetime

import pytest

import tests.integration.data_gen as data_gen
from database.uow import UnitOfWork
from domain.models import ActionType
from service.services import RecordService


@pytest.mark.asyncio
async def test_take_resource_success(record_service: RecordService) -> None:
    resource = await data_gen.added_resource()
    visitor = await data_gen.added_visitor()
    date = datetime.datetime.now() + datetime.timedelta(days=5)
    address = data_gen.random_str()

    result = await record_service.take_resource(resource.id, visitor.email, address, date)
    assert result.is_success
    record = result.unwrap()
    assert record.address == address
    assert record.return_date == date


@pytest.mark.asyncio
async def test_take_resource_409(record_service: RecordService) -> None:
    resource = await data_gen.added_resource()
    visitor = await data_gen.added_visitor()
    await data_gen.added_take_record(visitor, resource)
    date = datetime.datetime.now() + datetime.timedelta(days=5)
    address = data_gen.random_str()

    result = await record_service.take_resource(resource.id, visitor.email, address, date)
    assert result.is_failure
    assert result.error_code == 409


@pytest.mark.asyncio
async def test_take_resource_no_resource_404(record_service: RecordService) -> None:
    resource = await data_gen.added_resource()
    result = await record_service.take_resource(
        resource_id=resource.id,
        user_email=data_gen.random_str(),
        address=data_gen.random_str(),
        return_date=datetime.datetime.now() + datetime.timedelta(days=5)
    )
    assert result.is_failure
    assert result.error_code == 404


@pytest.mark.asyncio
async def test_take_resource_no_visitor_404(record_service: RecordService) -> None:
    visitor = await data_gen.added_visitor()
    result = await record_service.take_resource(
        resource_id=data_gen.random_number(),
        user_email=visitor.email,
        address=data_gen.random_str(),
        return_date=datetime.datetime.now() + datetime.timedelta(days=5)
    )
    assert result.is_failure
    assert result.error_code == 404


@pytest.mark.asyncio
async def test_return_success(record_service: RecordService) -> None:
    take_record = await data_gen.added_take_record()
    result = await record_service.return_resource(take_record.resource_id)
    dto = result.unwrap()
    assert dto.previous_visitor_email == take_record.user_email
    assert dto.new_visitor_email is None
    assert dto.resource.id == take_record.resource_id
    get_result = await record_service.get(take_record.id)
    assert get_result.unwrap().finished is True


@pytest.mark.asyncio
async def test_take_after_return(record_service: RecordService) -> None:
    take_record = await data_gen.added_take_record()
    await record_service.return_resource(take_record.resource_id)
    result = await record_service.take_resource(take_record.resource_id, take_record.user_email)
    assert result.unwrap().id != take_record.id


@pytest.mark.asyncio
async def test_return_and_transfer_to_next_user_success(record_service: RecordService, uow: UnitOfWork) -> None:
    resource = await data_gen.added_resource()
    visitor1 = await data_gen.added_visitor()
    visitor2 = await data_gen.added_visitor()
    take_record = await data_gen.added_take_record(visitor1, resource)
    queue_record = await data_gen.added_queue_record(visitor2, resource)
    result = await record_service.return_resource(take_record.resource_id)
    dto = result.unwrap()
    assert dto.previous_visitor_email == visitor1.email
    assert dto.new_visitor_email == visitor2.email
    assert dto.resource.id == resource.id
    async with uow:
        resource = await uow.resources.get(resource.id)
        assert resource.take_record.id == queue_record.id
        assert resource.take_record.user_email == visitor2.email
        assert resource.queue_records == []


@pytest.mark.asyncio
async def test_return_not_taken_417(record_service: RecordService) -> None:
    resource = await data_gen.added_resource()
    result = await record_service.return_resource(resource.id)
    assert result.is_failure
    assert result.error_code == 417


@pytest.mark.asyncio
async def test_enqueue_success(record_service: RecordService) -> None:
    take_record = await data_gen.added_take_record()
    visitor = await data_gen.added_visitor()
    result = await record_service.enqueue(take_record.resource_id, visitor.email)
    assert result.unwrap().enqueue_date is not None


@pytest.mark.asyncio
async def test_enqueue_409(record_service: RecordService) -> None:
    take_record = await data_gen.added_take_record()
    visitor = await data_gen.added_visitor()
    await record_service.enqueue(take_record.resource_id, visitor.email)
    result = await record_service.enqueue(take_record.resource_id, visitor.email)
    assert result.is_failure
    assert result.error_code == 409


@pytest.mark.asyncio
async def test_enqueue_no_visitor_404(record_service: RecordService) -> None:
    take_record = await data_gen.added_take_record()
    await data_gen.added_visitor()
    result = await record_service.enqueue(take_record.resource_id, data_gen.random_str())
    assert result.is_failure
    assert result.error_code == 404


@pytest.mark.asyncio
async def test_enqueue_no_resource_404(record_service: RecordService) -> None:
    await data_gen.added_take_record()
    visitor = await data_gen.added_visitor()
    result = await record_service.enqueue(data_gen.random_number(), visitor.email)
    assert result.is_failure
    assert result.error_code == 404


@pytest.mark.asyncio
async def test_leave_queue_success(record_service: RecordService) -> None:
    queue_record = await data_gen.added_queue_record()
    result = await record_service.leave_queue(queue_record.resource_id, queue_record.user_email)
    assert result.unwrap().id == queue_record.id
    get_record_result = await record_service.get(queue_record.id)
    assert get_record_result.is_failure


@pytest.mark.asyncio
async def test_leave_queue_no_queue_record_404(record_service: RecordService) -> None:
    resource = await data_gen.added_resource()
    visitor = await data_gen.added_visitor()
    result = await record_service.leave_queue(resource.id, visitor.email)
    assert result.is_failure
    assert result.error_code == 404


@pytest.mark.asyncio
async def test_leave_queue_no_resource_404(record_service: RecordService) -> None:
    visitor = await data_gen.added_visitor()
    result = await record_service.leave_queue(data_gen.random_number(), visitor.email)
    assert result.is_failure
    assert result.error_code == 404


@pytest.mark.asyncio
async def test_leave_queue_no_visitor_404(record_service: RecordService) -> None:
    resource = await data_gen.added_resource()
    result = await record_service.leave_queue(resource.id, data_gen.random_str())
    assert result.is_failure
    assert result.error_code == 404


@pytest.mark.asyncio
async def test_put_success(record_service: RecordService) -> None:
    take_record = await data_gen.added_take_record()
    return_date = datetime.datetime.now() + datetime.timedelta(days=400)
    address = data_gen.random_str()
    result = await record_service.put(take_record.id, address, return_date)
    updated_record = result.unwrap()
    assert updated_record.address == address
    assert updated_record.return_date == return_date


@pytest.mark.asyncio
async def test_put_404(record_service: RecordService) -> None:
    return_date = datetime.datetime.now() + datetime.timedelta(days=400)
    address = data_gen.random_str()
    result = await record_service.put(data_gen.random_number(), address, return_date)
    assert result.is_failure
    assert result.error_code == 404


@pytest.mark.asyncio
async def test_get_all_taken_success(record_service: RecordService) -> None:
    take_record1 = await data_gen.added_take_record()
    take_record2 = await data_gen.added_take_record()
    result = await record_service.get_all_taken()
    dtos = result.unwrap()
    assert take_record1.resource_id in [i.id for i in dtos]
    assert take_record2.resource_id in [i.id for i in dtos]


@pytest.mark.asyncio
async def test_get_all_taken_empty_list(record_service: RecordService) -> None:
    result = await record_service.get_all_taken()
    assert result.unwrap() == []


@pytest.mark.asyncio
async def test_get_expiring_success(record_service: RecordService) -> None:
    await data_gen.added_take_record()
    expired_record = await data_gen.added_expired_record()
    result = await record_service.get_expiring(2)
    dtos = result.unwrap()
    assert len(dtos) == 1
    assert set([i.record.id for i in dtos]) == {expired_record.id}


@pytest.mark.asyncio
async def test_get_expiring_empty_list(record_service: RecordService) -> None:
    result = await record_service.get_expiring(2)
    assert result.unwrap() == []


@pytest.mark.asyncio
async def test_get_available_action_take(record_service: RecordService) -> None:
    visitor = await data_gen.added_visitor()
    resource = await data_gen.added_resource()
    result = await record_service.get_available_action(resource.id, visitor.email)
    assert result.unwrap() == ActionType.TAKE


@pytest.mark.asyncio
async def test_get_available_action_return(record_service: RecordService) -> None:
    take_record = await data_gen.added_take_record()
    result = await record_service.get_available_action(take_record.resource.id, take_record.visitor.email)
    assert result.unwrap() == ActionType.RETURN


@pytest.mark.asyncio
async def test_get_available_action_queue(record_service: RecordService) -> None:
    take_record = await data_gen.added_take_record()
    visitor_without_resource = await data_gen.added_visitor()
    result = await record_service.get_available_action(take_record.resource.id, visitor_without_resource.email)
    assert result.unwrap() == ActionType.QUEUE


@pytest.mark.asyncio
async def test_get_available_action_leave(record_service: RecordService) -> None:
    visitor1 = await data_gen.added_visitor()
    visitor2 = await data_gen.added_visitor()
    resource = await data_gen.added_resource()
    await data_gen.added_take_record(visitor1, resource)
    await data_gen.added_queue_record(visitor2, resource)
    result = await record_service.get_available_action(resource.id, visitor2.email)
    assert result.unwrap() == ActionType.LEAVE


@pytest.mark.asyncio
async def test_get_available_action_no_resource_404(record_service: RecordService) -> None:
    visitor = await data_gen.added_visitor()
    result = await record_service.get_available_action(data_gen.random_number(), visitor.email)
    assert result.is_failure
    assert result.error_code == 404


@pytest.mark.asyncio
async def test_get_available_action_no_visitor_404(record_service: RecordService) -> None:
    resource = await data_gen.added_resource()
    result = await record_service.get_available_action(resource.id, data_gen.random_str())
    assert result.is_failure
    assert result.error_code == 404


@pytest.mark.asyncio
async def test_delete_old_finished_records_success(record_service: RecordService) -> None:
    await data_gen.added_take_record()
    return_date = datetime.datetime.now() - datetime.timedelta(days=101)
    finished_record = await data_gen.added_finished_record(return_date=return_date)
    await record_service.delete_old_finished_records(100)
    get_record_result = await record_service.get(finished_record.id)
    assert get_record_result.is_failure
