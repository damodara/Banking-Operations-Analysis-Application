import json
import os
import tempfile
from datetime import datetime
from unittest.mock import patch

import pandas as pd
import pytest

from config import PATH_TO_OPERATIONS
from src import services as s


def test_get_mobile_transactions_success() -> None:
    """Тест успешного получения мобильных транзакций"""
    transactions = s.get_mobile_transactions(str(PATH_TO_OPERATIONS), target_month=11, target_year=2021)
    assert isinstance(transactions, list)

    if transactions:  # Если есть транзакции с мобильными номерами
        for transaction in transactions:
            assert "date" in transaction
            assert "amount" in transaction
            assert "description" in transaction
            assert "category" in transaction
            assert isinstance(transaction["amount"], (int, float))
            assert isinstance(transaction["description"], str)


def test_get_mobile_transactions_empty_data() -> None:
    """Тест get_mobile_transactions с пустыми данными (mock)."""
    empty_df = pd.DataFrame()
    with patch("src.services.load_transactions_data", return_value=empty_df):
        transactions = s.get_mobile_transactions("dummy.xlsx")
        assert transactions == []


def test_get_mobile_transactions_missing_description_column() -> None:
    """Тест get_mobile_transactions с отсутствующей колонкой Описание (mock)."""
    df = pd.DataFrame({"other_column": [1, 2, 3]})
    with patch("src.services.load_transactions_data", return_value=df):
        transactions = s.get_mobile_transactions("dummy.xlsx")
        assert transactions == []


def test_get_mobile_transactions_with_mobile_numbers() -> None:
    """Тест get_mobile_transactions с данными, содержащими мобильные номера (mock)."""
    target_date = datetime(2021, 11, 15)
    df = pd.DataFrame(
        {
            "Дата операции": [target_date.strftime("%d.%m.%Y %H:%M:%S")],
            "Описание": ["Тинькофф Мобайл +7 995 555-55-55"],
            "Сумма операции": [-200.0],
            "Категория": ["Мобильная связь"],
        }
    )
    with patch("src.services.load_transactions_data", return_value=df):
        transactions = s.get_mobile_transactions("dummy.xlsx", target_month=11, target_year=2021)
        assert len(transactions) == 1
        assert transactions[0]["description"] == "Тинькофф Мобайл +7 995 555-55-55"
        assert transactions[0]["amount"] == -200.0
        assert transactions[0]["category"] == "Мобильная связь"


def test_get_mobile_transactions_without_mobile_numbers() -> None:
    """Тест get_mobile_transactions с данными без мобильных номеров (mock)."""
    target_date = datetime(2021, 11, 15)
    df = pd.DataFrame(
        {
            "Дата операции": [target_date.strftime("%d.%m.%Y %H:%M:%S")],
            "Описание": ["Обычная покупка в магазине"],
            "Сумма операции": [-100.0],
            "Категория": ["Супермаркеты"],
        }
    )
    with patch("src.services.load_transactions_data", return_value=df):
        transactions = s.get_mobile_transactions("dummy.xlsx", target_month=11, target_year=2021)
        assert transactions == []


def test_get_mobile_transactions_different_formats() -> None:
    """Тест get_mobile_transactions с разными форматами мобильных номеров (mock)."""
    target_date = datetime(2021, 11, 15)
    df = pd.DataFrame(
        {
            "Дата операции": [
                target_date.strftime("%d.%m.%Y %H:%M:%S"),
                target_date.strftime("%d.%m.%Y %H:%M:%S"),
                target_date.strftime("%d.%m.%Y %H:%M:%S"),
                target_date.strftime("%d.%m.%Y %H:%M:%S"),
            ],
            "Описание": [
                "МТС +7 921 11-22-33",
                "Тинькофф 8 995 555 55 55",
                "Билайн +79213334455",
                "МегаФон 8(921)333-44-55",
            ],
            "Сумма операции": [-100.0, -200.0, -150.0, -50.0],
            "Категория": ["МТС", "Тинькофф", "Билайн", "МегаФон"],
        }
    )
    with patch("src.services.load_transactions_data", return_value=df):
        transactions = s.get_mobile_transactions("dummy.xlsx", target_month=11, target_year=2021)
        assert len(transactions) == 4
        descriptions = [t["description"] for t in transactions]
        assert "МТС +7 921 11-22-33" in descriptions
        assert "Тинькофф 8 995 555 55 55" in descriptions
        assert "Билайн +79213334455" in descriptions
        assert "МегаФон 8(921)333-44-55" in descriptions


def test_get_mobile_transactions_month_filter() -> None:
    """Тест фильтрации get_mobile_transactions по месяцу (mock)."""
    target_date = datetime(2021, 11, 15)
    other_date = datetime(2021, 10, 15)
    df = pd.DataFrame(
        {
            "Дата операции": [
                target_date.strftime("%d.%m.%Y %H:%M:%S"),  # ноябрь
                other_date.strftime("%d.%m.%Y %H:%M:%S"),  # октябрь
            ],
            "Описание": ["МТС +7 921 11-22-33", "Тинькофф +7 995 555-55-55"],
            "Сумма операции": [-100.0, -200.0],
            "Категория": ["МТС", "Тинькофф"],
        }
    )
    with patch("src.services.load_transactions_data", return_value=df):
        # Тестируем фильтрацию по ноябрю
        transactions = s.get_mobile_transactions("dummy.xlsx", target_month=11, target_year=2021)
        assert len(transactions) == 1
        assert transactions[0]["description"] == "МТС +7 921 11-22-33"
        # Тестируем фильтрацию по октябрю
        transactions = s.get_mobile_transactions("dummy.xlsx", target_month=10, target_year=2021)
        assert len(transactions) == 1
        assert transactions[0]["description"] == "Тинькофф +7 995 555-55-55"


def test_find_mobile_numbers_in_text_success() -> None:
    """Тест успешного поиска мобильных номеров в тексте"""
    text = "Я МТС +7 921 11-22-33 и Тинькофф Мобайл +7 995 555-55-55"
    numbers = s.find_mobile_numbers_in_text(text)
    assert len(numbers) == 2
    assert "+7 921 11-22-33" in numbers
    assert "+7 995 555-55-55" in numbers


def test_find_mobile_numbers_in_text_different_formats() -> None:
    """Тест поиска мобильных номеров в разных форматах"""
    text = "МТС +7 921 11-22-33, Тинькофф 8 995 555 55 55, Билайн +79213334455, МегаФон 8(921)333-44-55"
    numbers = s.find_mobile_numbers_in_text(text)
    assert len(numbers) == 4
    assert "+7 921 11-22-33" in numbers
    assert "8 995 555 55 55" in numbers
    assert "+79213334455" in numbers
    assert "8(921)333-44-55" in numbers


def test_find_mobile_numbers_in_text_no_numbers() -> None:
    """Тест поиска мобильных номеров в тексте без номеров"""
    text = "Обычная покупка в магазине без номеров"
    numbers = s.find_mobile_numbers_in_text(text)
    assert numbers == []


def test_find_mobile_numbers_in_text_empty() -> None:
    """Тест поиска мобильных номеров в пустом тексте"""
    assert s.find_mobile_numbers_in_text("") == []
    assert s.find_mobile_numbers_in_text(None) == []
    assert s.find_mobile_numbers_in_text(123) == []


def test_find_mobile_numbers_in_text_single_number() -> None:
    """Тест поиска одного мобильного номера"""
    text = "МТС +7 921 11-22-33"
    numbers = s.find_mobile_numbers_in_text(text)
    assert len(numbers) == 1
    assert numbers[0] == "+7 921 11-22-33"


def test_get_mobile_transactions_current_month() -> None:
    """Тест get_mobile_transactions с текущим месяцем (без указания параметров)"""
    transactions = s.get_mobile_transactions(str(PATH_TO_OPERATIONS))
    assert isinstance(transactions, list)
    # Проверяем, что функция не падает и возвращает список
    for transaction in transactions:
        assert "date" in transaction
        assert "amount" in transaction
        assert "description" in transaction
        assert "category" in transaction


def test_get_mobile_transactions_file_not_found() -> None:
    """Тест get_mobile_transactions с несуществующим файлом"""
    with pytest.raises(FileNotFoundError):
        s.get_mobile_transactions("nonexistent_file.xlsx")


def test_get_mobile_transactions_mixed_data() -> None:
    """Тест get_mobile_transactions со смешанными данными (с номерами и без) (mock)."""
    target_date = datetime(2021, 11, 15)
    df = pd.DataFrame(
        {
            "Дата операции": [
                target_date.strftime("%d.%m.%Y %H:%M:%S"),
                target_date.strftime("%d.%m.%Y %H:%M:%S"),
                target_date.strftime("%d.%m.%Y %H:%M:%S"),
            ],
            "Описание": [
                "МТС +7 921 11-22-33",  # с номером
                "Обычная покупка",  # без номера
                "Тинькофф +7 995 555-55-55",  # с номером
            ],
            "Сумма операции": [-100.0, -50.0, -200.0],
            "Категория": ["МТС", "Супермаркеты", "Тинькофф"],
        }
    )
    with patch("src.services.load_transactions_data", return_value=df):
        transactions = s.get_mobile_transactions("dummy.xlsx", target_month=11, target_year=2021)
        assert len(transactions) == 2  # только 2 транзакции с номерами
        descriptions = [t["description"] for t in transactions]
        assert "МТС +7 921 11-22-33" in descriptions
        assert "Тинькофф +7 995 555-55-55" in descriptions
        assert "Обычная покупка" not in descriptions

    # Доп. покрытие search_phone_transactions
    transactions_list = [
        {
            "Дата операции": "18.11.2021 21:15:27",
            "Описание": "Тинькофф Мобайл +7 995 555-55-55",
            "Сумма операции": -200.0,
            "Категория": "Мобильная связь",
        },
        {
            "Дата операции": "18.11.2021 21:15:27",
            "Описание": "Без номера",
            "Сумма операции": -10.0,
            "Категория": "Другое",
        },
    ]
    json_res = s.search_phone_transactions(transactions_list)
    payload = json.loads(json_res)
    assert isinstance(payload, list)
    assert len(payload) == 1
    item = payload[0]
    assert set(["date", "amount", "description", "category"]).issubset(item.keys())
    assert item["description"].endswith("+7 995 555-55-55")


@pytest.mark.parametrize(
    "text, expected",
    [
        ("МТС +7 921 11-22-33", ["+7 921 11-22-33"]),
        ("Тинькофф 8 995 555 55 55", ["8 995 555 55 55"]),
        ("Билайн +79213334455", ["+79213334455"]),
        ("МегаФон 8(921)333-44-55", ["8(921)333-44-55"]),
        (
            "Я МТС +7 921 11-22-33 и Тинькофф +7 995 555-55-55",
            ["+7 921 11-22-33", "+7 995 555-55-55"],
        ),
    ],
)
def test_find_mobile_numbers_parametrized(text, expected) -> None:
    numbers = s.find_mobile_numbers_in_text(text)
    assert isinstance(numbers, list)
    for num in expected:
        assert num in numbers
