import pytest

import service.resource_checker as resource_checker


@pytest.mark.parametrize("email", ["mnoskov@skbkontur.ru", "a.ivanov@skbkontur.ru"])
def test_is_kontur_email(email: str) -> None:
    assert resource_checker.is_kontur_email(email).string == email


@pytest.mark.parametrize("email", ["mnoskov@skontur.ru", "nnn@gmail.com"])
def test_is_kontur_email_negative_cases(email: str) -> None:
    assert resource_checker.is_kontur_email(email) is None
