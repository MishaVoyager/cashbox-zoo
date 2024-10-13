import pytest

import helpers.tghelper as tghelper


# noinspection Mypy
class TestPaginator:

    @pytest.mark.parametrize("part, result_length, max_index, expected_left, expected_right", [
        (1, 10, 500, 0, 9),
        (2, 10, 500, 10, 19),
        (3, 10, 500, 20, 29),
        (1, 10, 0, 0, 0),
        (1, 100, 99, 0, 99),
        (1, 5, 500, 0, 4),
        (2, 5, 500, 5, 9),
        (2, 10, 15, 10, 15)
    ])
    def test_get_left_and_right_border(self, part, result_length, max_index, expected_left, expected_right) -> None:
        paginator = tghelper.Paginator(part, [0] * (max_index + 1), result_length, 3)
        assert paginator.get_array_indexes() == (expected_left, expected_right)

    @pytest.mark.parametrize("part, max_part, page_buttons, expected", [
        (1, 1, 3, (None, None, None)),
        (1, 2, 3, (1, 2, None)),
        (1, 3, 3, (1, 2, 3)),
        (2, 3, 3, (1, 2, 3)),
        (1, 100, 3, (1, 2, 3)),
        (3, 3, 3, (1, 2, 3)),
        (2, 2, 3, (1, 2, None)),
        (1, 100, 4, (1, 2, 3, 4)),
        (2, 100, 4, (1, 2, 3, 4)),
        (3, 100, 4, (2, 3, 4, 5)),
        (4, 100, 4, (3, 4, 5, 6)),
        (5, 100, 4, (4, 5, 6, 7)),
        (5, 5, 4, (2, 3, 4, 5)),
        (1, 4, 4, (1, 2, 3, 4)),
        (1, 3, 4, (1, 2, 3, None)),
        (1, 2, 4, (1, 2, None, None)),
        (1, 1, 4, (None, None, None, None)),
        (1, 100, 5, (1, 2, 3, 4, 5)),
        (4, 5, 5, (1, 2, 3, 4, 5)),
        (4, 100, 5, (2, 3, 4, 5, 6)),
        (5, 5, 5, (1, 2, 3, 4, 5)),
        (1, 1, 5, (None, None, None, None, None)),
        (1, 2, 5, (1, 2, None, None, None)),
        (1, 3, 5, (1, 2, 3, None, None)),
        (100, 100, 5, (96, 97, 98, 99, 100)),
        (97, 100, 5, (95, 96, 97, 98, 99))
    ])
    def test_get_index_list(self, part, max_part, page_buttons, expected) -> None:
        paginator = tghelper.Paginator(part, [0] * 10 * max_part, 10, page_buttons)
        assert paginator.get_pages_numbers() == expected
