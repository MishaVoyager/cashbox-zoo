import pytest

import tests.integration.data_gen as data_gen
from configs.config import Settings
from domain.models import Category
from service.services import CategoryService


@pytest.mark.asyncio
async def test_get_success(category_service: CategoryService) -> None:
    category = data_gen.added_category()
    result = await category_service.get(category.name)
    assert result.unwrap().name == category.name


@pytest.mark.asyncio
async def test_get_404(category_service: CategoryService) -> None:
    result = await category_service.get(data_gen.random_str())
    assert result.is_failure
    assert result.error_code == 404


@pytest.mark.asyncio
async def test_add_success(category_service: CategoryService) -> None:
    category = Category(name=data_gen.random_str())
    result = await category_service.add(category)
    assert result.is_success
    result = await category_service.get(category.name)
    assert result.unwrap().name == category.name


@pytest.mark.asyncio
async def test_add_409(category_service: CategoryService) -> None:
    result = await category_service.add(data_gen.random_category())
    assert result.is_failure
    assert result.error_code == 409


@pytest.mark.asyncio
async def test_delete_success(category_service: CategoryService) -> None:
    category = data_gen.added_category()
    result = await category_service.delete(category.name)
    assert result.unwrap().name == category.name
    result = await category_service.get(category.name)
    assert result.is_failure


@pytest.mark.asyncio
async def test_delete_404(category_service: CategoryService) -> None:
    result = await category_service.delete(data_gen.random_str())
    assert result.is_failure
    assert result.error_code == 404


@pytest.mark.asyncio
async def test_get_all_success(category_service: CategoryService) -> None:
    categories_from_settings = Settings().get_categories()
    result = await category_service.get_all()
    categories = result.unwrap()
    assert result.is_success
    assert len(categories) == len(categories_from_settings)
    assert set([i.name for i in categories]) == set(categories_from_settings)
