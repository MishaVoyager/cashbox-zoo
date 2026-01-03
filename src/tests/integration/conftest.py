import pytest

from service.database_service import DatabaseService
from service.orm_uow import OrmUnitOfWork
from service.services import CategoryService, ResourceService, VisitorService, RecordService


@pytest.fixture()
def uow() -> OrmUnitOfWork:
    return OrmUnitOfWork()


@pytest.fixture(autouse=True)
async def clean_db_after_test(uow: OrmUnitOfWork):  # type: ignore
    await DatabaseService(uow).init()
    yield
    await DatabaseService(uow).drop_base()


@pytest.fixture
def category_service(uow: OrmUnitOfWork) -> CategoryService:
    return CategoryService(uow)


@pytest.fixture
def resource_service(uow: OrmUnitOfWork) -> ResourceService:
    return ResourceService(uow)


@pytest.fixture
def visitor_service(uow: OrmUnitOfWork) -> VisitorService:
    return VisitorService(uow)


@pytest.fixture
def record_service(uow: OrmUnitOfWork) -> RecordService:
    return RecordService(uow)
