import pytest

import tests.integration.data_gen as data_gen
from service.services import VisitorService


@pytest.mark.asyncio
async def test_get_success(visitor_service: VisitorService) -> None:
    visitor = await data_gen.added_visitor()
    result = await visitor_service.get(visitor.email)
    assert result.is_success
    assert result.unwrap().id == visitor.id


@pytest.mark.asyncio
async def test_get_404(visitor_service: VisitorService) -> None:
    result = await visitor_service.get(data_gen.random_str())
    assert result.is_failure
    assert result.error_code == 404


@pytest.mark.asyncio
async def test_get_by_chat_id_success(visitor_service: VisitorService) -> None:
    visitor = await data_gen.added_visitor()
    result = await visitor_service.get_by_chat_id(visitor.chat_id)
    assert result.is_success
    assert result.unwrap().id == visitor.id


@pytest.mark.asyncio
async def test_get_by_chat_id_404(visitor_service: VisitorService) -> None:
    result = await visitor_service.get_by_chat_id(data_gen.random_number())
    assert result.is_failure
    assert result.error_code == 404


@pytest.mark.asyncio
async def test_get_by_id_success(visitor_service: VisitorService) -> None:
    visitor = await data_gen.added_visitor()
    result = await visitor_service.get_by_id(visitor.id)
    assert result.is_success
    assert result.unwrap().id == visitor.id


@pytest.mark.asyncio
async def test_get_by_id_404(visitor_service: VisitorService) -> None:
    result = await visitor_service.get_by_id(data_gen.random_number())
    assert result.is_failure
    assert result.error_code == 404


@pytest.mark.asyncio
async def test_get_all_success(visitor_service: VisitorService) -> None:
    visitor1 = await data_gen.added_visitor()
    visitor2 = await data_gen.added_visitor()
    result = await visitor_service.get_all()
    emails = [i.email for i in result.unwrap()]
    assert visitor1.email in emails and visitor2.email in emails


@pytest.mark.asyncio
async def test_get_all_empty_list(visitor_service: VisitorService) -> None:
    result = await visitor_service.get_all()
    assert result.is_success
    assert result.unwrap() == []


@pytest.mark.asyncio
async def test_delete_success(visitor_service: VisitorService) -> None:
    visitor = await data_gen.added_visitor()
    result = await visitor_service.delete(visitor.email)
    assert result.is_success
    get_result = await visitor_service.get(visitor.email)
    assert get_result.is_failure


@pytest.mark.asyncio
async def test_delete_404(visitor_service: VisitorService) -> None:
    result = await visitor_service.delete(data_gen.random_str())
    assert result.is_failure
    assert result.error_code == 404


@pytest.mark.asyncio
async def test_search_success(visitor_service: VisitorService) -> None:
    visitor1 = await data_gen.added_visitor()
    await data_gen.added_visitor()
    search_result = await visitor_service.search(visitor1.email[0:10])
    visitors = search_result.unwrap()
    assert visitor1.email in [i.email for i in visitors]


@pytest.mark.asyncio
async def test_search_empty_list(visitor_service: VisitorService) -> None:
    search_result = await visitor_service.search(data_gen.random_str())
    assert search_result.is_success
    assert search_result.unwrap() == []


@pytest.mark.asyncio
async def test_add_success(visitor_service: VisitorService) -> None:
    visitor = data_gen.random_visitor()
    result = await visitor_service.add_visitor(visitor)
    assert result.is_success
    assert result.unwrap().email == visitor.email
    added_visitor = await visitor_service.get(visitor.email)
    assert added_visitor.is_success
    assert added_visitor.unwrap().id == visitor.id


@pytest.mark.asyncio
async def test_add_409(visitor_service: VisitorService) -> None:
    visitor = await data_gen.added_visitor()
    add_result = await visitor_service.add_visitor(visitor)
    assert add_result.is_failure
    assert add_result.error_code == 409


@pytest.mark.asyncio
async def test_finished_records_success(visitor_service: VisitorService) -> None:
    visitor = await data_gen.added_visitor()
    finished_record1 = await data_gen.added_finished_record(visitor=visitor)
    finished_record2 = await data_gen.added_finished_record(visitor=visitor)
    result = await visitor_service.get_finished_records(visitor.id)
    assert result.is_success
    assert set([i.record_id for i in result.unwrap()]) == {finished_record1.id, finished_record2.id}


@pytest.mark.asyncio
async def test_finished_records_empty_list(visitor_service: VisitorService) -> None:
    visitor = await data_gen.added_visitor()
    result = await visitor_service.get_finished_records(visitor.id)
    assert result.is_success
    assert result.unwrap() == []


@pytest.mark.asyncio
async def test_get_taken_resources_success(visitor_service: VisitorService) -> None:
    visitor = await data_gen.added_visitor()
    take_record = await data_gen.added_take_record(visitor=visitor)
    await data_gen.added_queue_record(visitor=visitor)
    result = await visitor_service.get_taken_resources(take_record.visitor)
    assert result.is_success
    assert [i.id for i in result.unwrap()] == [take_record.resource_id]


@pytest.mark.asyncio
async def test_get_taken_resources_empty_list(visitor_service: VisitorService) -> None:
    visitor = await data_gen.added_visitor()
    result = await visitor_service.get_taken_resources(visitor)
    assert result.is_success
    assert result.unwrap() == []


@pytest.mark.asyncio
async def test_get_taken_resources_404(visitor_service: VisitorService) -> None:
    visitor = data_gen.random_visitor()
    result = await visitor_service.get_taken_resources(visitor)
    assert result.is_failure
    assert result.error_code == 404


@pytest.mark.asyncio
async def test_get_queue_success(visitor_service: VisitorService) -> None:
    visitor = await data_gen.added_visitor()
    await data_gen.added_take_record(visitor=visitor)
    queue_record = await data_gen.added_queue_record(visitor=visitor)
    result = await visitor_service.get_queue(queue_record.visitor)
    assert result.is_success
    assert [i.id for i in result.unwrap()] == [queue_record.resource_id]
    assert result.unwrap()[0].name == queue_record.resource.name


@pytest.mark.asyncio
async def test_get_queue_empty_list(visitor_service: VisitorService) -> None:
    visitor = await data_gen.added_visitor()
    result = await visitor_service.get_queue(visitor)
    assert result.is_success
    assert result.unwrap() == []


@pytest.mark.asyncio
async def test_get_queue_404(visitor_service: VisitorService) -> None:
    visitor = data_gen.random_visitor()
    result = await visitor_service.get_queue(visitor)
    assert result.is_failure
    assert result.error_code == 404


@pytest.mark.asyncio
async def test_auth_existed_visitor_success(visitor_service: VisitorService) -> None:
    visitor = await data_gen.added_visitor()
    visitor.chat_id = 414144
    result = await visitor_service.auth(visitor)
    assert result.is_success
    assert result.unwrap().chat_id == 414144


@pytest.mark.asyncio
async def test_auth_new_visitor_success(visitor_service: VisitorService) -> None:
    visitor = data_gen.random_visitor()
    result = await visitor_service.auth(visitor)
    assert result.is_success
    assert result.unwrap().chat_id == visitor.chat_id


@pytest.mark.asyncio
async def test_add_without_auth_success(visitor_service: VisitorService) -> None:
    email = data_gen.random_email()
    result = await visitor_service.add_without_auth(email)
    visitor = result.unwrap()
    assert visitor.email == email
    assert visitor.chat_id is None


@pytest.mark.asyncio
async def test_add_without_auth_409(visitor_service: VisitorService) -> None:
    visitor = await data_gen.added_visitor()
    result = await visitor_service.add_without_auth(visitor.email)
    assert result.is_failure
    assert result.error_code == 409


@pytest.mark.asyncio
async def test_update_success(visitor_service: VisitorService) -> None:
    email = data_gen.random_email()
    comment = data_gen.random_str()
    visitor = await data_gen.added_visitor()
    result = await visitor_service.update(visitor.id, email, comment)
    updated_visitor = result.unwrap()
    assert updated_visitor.email == email
    assert updated_visitor.comment == comment


@pytest.mark.asyncio
async def test_update_404(visitor_service: VisitorService) -> None:
    result = await visitor_service.update(data_gen.random_number(), "", "")
    assert result.is_failure
    assert result.error_code == 404
