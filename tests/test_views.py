import pytest

from src.views import greetings


@pytest.mark.parametrize(
    "input_date, expected_result",
    [
        ("2025-09-14 04:10:05", "Доброй ночи"),
        ("2025-09-14 05:10:05", "Доброе утро"),
        ("2025-09-14 12:10:05", "Добрый день"),
        ("2025-09-14 18:10:05", "Добрый вечер"),
    ],
)
def test_greetings_valid(input_date, expected_result):
    assert greetings(input_date) == expected_result


@pytest.mark.parametrize(
    "invalid_input",
    [
        "",
        "abc",
        "2023-10-10",
        "2023-10-10T10:30:00Z",
        "2023-10-10 25:30:00",
    ],
)
def test_greetings_invalid(invalid_input):
    assert greetings(invalid_input) == "Неверный формат времени"
