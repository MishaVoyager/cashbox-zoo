import datetime

from domain.resource_info import ResourceInfoDTO


def test_only_required_fields() -> None:
    ResourceInfoDTO(
        id=1,
        name="name",
        category_name="Онлайн-касса",
        vendor_code="f4194"
    )


def test_valid_dates_as_str() -> None:
    result = ResourceInfoDTO(
        id=1,
        name="name",
        category_name="Онлайн-касса",
        vendor_code="f4194",
        reg_date="30.08.2024",
        return_date="12.12.2999"
    )
    assert result.reg_date.year == 2024
    assert result.return_date.year == 2999


def test_valid_dates_as_datetime() -> None:
    result = ResourceInfoDTO(
        id=1,
        name="name",
        category_name="Онлайн-касса",
        vendor_code="f4194",
        reg_date=datetime.datetime(day=30, month=8, year=2024),
        return_date=datetime.datetime(day=12, month=12, year=2999)
    )
    assert result.reg_date.year == 2024
    assert result.return_date.year == 2999


def test_none_fields() -> None:
    result = ResourceInfoDTO(
        id=1,
        name="name",
        category_name="Онлайн-касса",
        vendor_code="f4194",
        reg_date=None,
        return_date=None,
        firmware=None,
        comment=None,
        user_email=None,
        address=None
    )
    assert result.reg_date is None
    assert result.return_date is None


def test_reg_date_incorrect_format() -> None:
    try:
        ResourceInfoDTO(
            id=1,
            name="name",
            category_name="Онлайн-касса",
            vendor_code="f4194",
            reg_date="300.08.2024",
            return_date="300.08.2024"
        )
    except ValueError as e:
        names = list()
        types = list()
        for error in e.errors():
            names.append(error['loc'][0])
            types.append(error['type'])
        assert names == ["reg_date", "return_date"]
        assert types == ["value_error", "value_error"]


def test_check_user_email_valid() -> None:
    ResourceInfoDTO(
        id=1,
        name="name",
        category_name="Онлайн-касса",
        vendor_code="f4194",
        user_email="test@skbkontur.ru"
    )


def test_check_user_email_invalid() -> None:
    try:
        ResourceInfoDTO(
            id=1,
            name="name",
            category_name="Онлайн-касса",
            vendor_code="f4194",
            user_email="test@skbkontur.ru"
        )
    except ValueError as e:
        error = e.errors()[0]
        assert error['loc'][0] == "user_email"
        assert error['type'] == "value_error"


def test_description() -> None:
    info = ResourceInfoDTO(
        id=1,
        name="name",
        category_name="Онлайн-касса",
        vendor_code="f4194",
        reg_date="30.08.2024",
        firmware="прошивка",
        comment="коммент",
        user_email="test@skbkontur.ru",
        address="адрес",
        return_date="12.12.2999"
    )
    assert info.description() == """1. name (Онлайн-касса)
Артикул: f4194
Зарегистрирован 30.08.2024
Прошивка: прошивка
Коммент: коммент
У пользователя test@skbkontur.ru
Освободится: 12.12.2999
Находится: адрес"""
