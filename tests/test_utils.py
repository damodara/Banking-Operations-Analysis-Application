import json
import os
import tempfile
from datetime import datetime

import pandas as pd
import pytest

from config import PATH_TO_OPERATIONS, PATH_TO_USER_SETTINGS
from src import utils as u


def test_build_cards_structure() -> None:
    cards = u.build_cards(str(PATH_TO_OPERATIONS))
    assert isinstance(cards, list)
    if cards:
        sample = cards[0]
        assert set(["last_digits", "total_spent", "cashback"]).issubset(sample.keys())
        assert isinstance(sample["last_digits"], str)
        assert isinstance(sample["total_spent"], float)
        assert isinstance(sample["cashback"], float)


def test_build_cards_with_month() -> None:
    """Тест build_cards с указанным месяцем"""
    cards = u.build_cards(str(PATH_TO_OPERATIONS), target_month=9, target_year=2025)
    assert isinstance(cards, list)
    # Проверяем структуру карт
    if cards:
        sample = cards[0]
        assert set(["last_digits", "total_spent", "cashback"]).issubset(sample.keys())
        assert isinstance(sample["last_digits"], str)
        assert isinstance(sample["total_spent"], float)
        assert isinstance(sample["cashback"], float)


def test_top_transactions_by_payment_order_and_shape() -> None:
    top = u.top_transactions_by_payment(str(PATH_TO_OPERATIONS), n=5)
    assert isinstance(top, list)
    assert len(top) <= 5

    for item in top:
        assert set(["date", "amount", "category", "description"]).issubset(item.keys())

    amounts_abs = [abs(x["amount"]) for x in top]
    assert amounts_abs == sorted(amounts_abs, reverse=True)


def test_top_transactions_with_month() -> None:
    """Тест top_transactions_by_payment с указанным месяцем"""
    top = u.top_transactions_by_payment(str(PATH_TO_OPERATIONS), n=5, target_month=9, target_year=2025)
    assert isinstance(top, list)
    assert len(top) <= 5

    for item in top:
        assert set(["date", "amount", "category", "description"]).issubset(item.keys())

    amounts_abs = [abs(x["amount"]) for x in top]
    assert amounts_abs == sorted(amounts_abs, reverse=True)


def test_get_currency_rates_static_fallback(monkeypatch):
    def fake_get(*args, **kwargs):
        raise RuntimeError("network disabled in test")

    monkeypatch.setattr(u.requests, "get", fake_get)
    res = u.get_currency_rates(["USD", "EUR"], use_static_fallback=True)
    assert isinstance(res, list)
    mapping = {x["currency"]: x["rate"] for x in res}
    assert mapping["USD"] == pytest.approx(73.21, rel=0, abs=0.01)
    assert mapping["EUR"] == pytest.approx(87.08, rel=0, abs=0.01)


def test_get_stock_prices_network_error(monkeypatch):
    """Тест get_stock_prices с отключенной сетью"""

    def fake_read_csv(*args, **kwargs):
        raise RuntimeError("no csv in test")

    def fake_get(*args, **kwargs):
        raise RuntimeError("network disabled in test")

    monkeypatch.setattr(pd, "read_csv", fake_read_csv)
    monkeypatch.setattr(u.requests, "get", fake_get)

    tickers = ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"]
    res = u.get_stock_prices(tickers)
    assert isinstance(res, list)
    assert len(res) == len(tickers)
    # При ошибке сети все цены должны быть None
    for item in res:
        assert item["price"] is None


def test_load_transactions_data_success() -> None:
    df = u.load_transactions_data(str(PATH_TO_OPERATIONS))
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    expected_cols = ["Номер карты", "Сумма операции", "Кэшбэк", "Дата платежа"]
    for col in expected_cols:
        assert col in df.columns


def test_load_transactions_data_file_not_found() -> None:
    with pytest.raises(FileNotFoundError, match="XLSX-файл не найден"):
        u.load_transactions_data("nonexistent_file.xlsx")


def test_process_transactions_structure() -> None:
    df = u.process_transactions(str(PATH_TO_OPERATIONS))
    assert isinstance(df, pd.DataFrame)
    expected_cols = ["Номер карты", "Сумма_операций", "Кешбек"]
    for col in expected_cols:
        assert col in df.columns
    assert df["Номер карты"].dtype == "object"


def test_load_user_settings_success() -> None:
    settings = u.load_user_settings(str(PATH_TO_USER_SETTINGS))
    assert isinstance(settings, list)
    if settings:
        assert isinstance(settings[0], dict)
        expected_keys = ["user_currencies", "user_stocks"]
        for key in expected_keys:
            assert key in settings[0]


def test_load_user_settings_file_not_found() -> None:
    settings = u.load_user_settings("nonexistent_settings.json")
    assert settings == []


def test_load_user_settings_invalid_json() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("invalid json content")
        temp_path = f.name
    try:
        settings = u.load_user_settings(temp_path)
        assert settings == []
    finally:
        os.unlink(temp_path)


def test_load_user_settings_non_list() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"not": "a list"}, f)
        temp_path = f.name

    try:
        settings = u.load_user_settings(temp_path)
        assert settings == []
    finally:
        os.unlink(temp_path)


def test_get_currency_rates_without_fallback(monkeypatch):
    def fake_get(*args, **kwargs):
        raise RuntimeError("network disabled in test")

    monkeypatch.setattr(u.requests, "get", fake_get)
    res = u.get_currency_rates(["USD", "EUR"], use_static_fallback=False)
    assert isinstance(res, list)
    assert len(res) == 2
    for item in res:
        assert item["rate"] is None


def test_get_currency_rates_empty_list() -> None:
    res = u.get_currency_rates([])
    assert res == []


def test_get_stock_prices_empty_list() -> None:
    res = u.get_stock_prices([])
    assert res == []


def test_get_currency_rates_unknown_currency() -> None:
    res = u.get_currency_rates(["UNKNOWN"], use_static_fallback=True)
    assert isinstance(res, list)
    assert len(res) == 1
    assert res[0]["currency"] == "UNKNOWN"
    assert res[0]["rate"] is None


def test_build_cards_empty_data() -> None:
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        empty_df = pd.DataFrame()
        empty_df.to_excel(f.name, index=False)
        temp_path = f.name

    try:
        cards = u.build_cards(temp_path)
        assert cards == []
    finally:
        os.unlink(temp_path)


def test_top_transactions_empty_data() -> None:
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        empty_df = pd.DataFrame()
        empty_df.to_excel(f.name, index=False)
        temp_path = f.name

    try:
        top = u.top_transactions_by_payment(temp_path, n=5)
        assert top == []
    finally:
        os.unlink(temp_path)


def test_get_stock_prices_unknown_ticker() -> None:
    """Тест get_stock_prices с неизвестным тикером"""
    res = u.get_stock_prices(["UNKNOWN"])
    assert isinstance(res, list)
    assert len(res) == 1
    assert res[0]["stock"] == "UNKNOWN"
    assert res[0]["price"] is None


def test_get_stock_prices_mixed_tickers(monkeypatch):
    """Тест get_stock_prices со смешанными тикерами (известные и неизвестные)"""

    def fake_read_csv(*args, **kwargs):
        raise RuntimeError("no csv in test")

    def fake_get(*args, **kwargs):
        raise RuntimeError("network disabled in test")

    monkeypatch.setattr(pd, "read_csv", fake_read_csv)
    monkeypatch.setattr(u.requests, "get", fake_get)

    tickers = ["AAPL", "UNKNOWN", "MSFT"]
    res = u.get_stock_prices(tickers)
    assert isinstance(res, list)
    assert len(res) == 3

    # При ошибке сети все цены должны быть None
    for item in res:
        assert item["price"] is None


def test_get_currency_rates_mixed_currencies() -> None:
    """Тест get_currency_rates со смешанными валютами (известные и неизвестные)"""
    res = u.get_currency_rates(["USD", "UNKNOWN", "EUR"], use_static_fallback=True)
    assert isinstance(res, list)
    assert len(res) == 3

    mapping = {x["currency"]: x["rate"] for x in res}
    # USD и EUR должны иметь статические значения, UNKNOWN - None
    assert mapping["USD"] is not None
    assert mapping["UNKNOWN"] is None
    assert mapping["EUR"] is not None


def test_process_transactions_empty_data() -> None:
    """Тест process_transactions с пустыми данными"""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        empty_df = pd.DataFrame()
        empty_df.to_excel(f.name, index=False)
        temp_path = f.name

    try:
        df = u.process_transactions(temp_path)
        assert isinstance(df, pd.DataFrame)
        assert df.empty
        expected_cols = ["Номер карты", "Сумма_операций", "Кешбек"]
        assert list(df.columns) == expected_cols
    finally:
        os.unlink(temp_path)


def test_process_transactions_missing_columns() -> None:
    """Тест process_transactions с отсутствующими колонками"""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        df = pd.DataFrame({"other_column": [1, 2, 3]})
        df.to_excel(f.name, index=False)
        temp_path = f.name

    try:
        result = u.process_transactions(temp_path)
        assert isinstance(result, pd.DataFrame)
        assert result.empty
        expected_cols = ["Номер карты", "Сумма_операций", "Кешбек"]
        assert list(result.columns) == expected_cols
    finally:
        os.unlink(temp_path)


def test_process_transactions_month_filter():
    """Тест фильтрации process_transactions по указанному месяцу"""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        # Создаем данные с разными месяцами
        target_date = datetime(2025, 9, 15)  # сентябрь 2025
        other_date = datetime(2025, 8, 15)   # август 2025
        
        data = {
            "Дата операции": [
                target_date.strftime("%d.%m.%Y %H:%M:%S"),  # целевой месяц
                other_date.strftime("%d.%m.%Y %H:%M:%S"),   # другой месяц
                target_date.strftime("%d.%m.%Y %H:%M:%S"),  # целевой месяц
            ],
            "Номер карты": ["*7197", "*5091", "*7197"],
            "Сумма операции": [-100.0, -200.0, -150.0],
            "Кэшбэк": [1.0, 2.0, 1.5]
        }
        df = pd.DataFrame(data)
        df.to_excel(f.name, index=False)
        temp_path = f.name
    
    try:
        result = u.process_transactions(temp_path, target_month=9, target_year=2025)
        # Должны остаться только транзакции целевого месяца
        assert not result.empty
        # Проверяем, что есть только карта *7197 (2 транзакции целевого месяца)
        assert len(result) == 1
        assert result.iloc[0]["Номер карты"] == "*7197"
        assert result.iloc[0]["Сумма_операций"] == -250.0  # -100 + -150
        assert result.iloc[0]["Кешбек"] == 2.5  # 1.0 + 1.5
    finally:
        os.unlink(temp_path)


def test_top_transactions_month_filter():
    """Тест фильтрации top_transactions по указанному месяцу"""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        # Создаем данные с разными месяцами
        target_date = datetime(2025, 9, 15)  # сентябрь 2025
        other_date = datetime(2025, 8, 15)   # август 2025
        
        data = {
            "Дата операции": [
                target_date.strftime("%d.%m.%Y %H:%M:%S"),  # целевой месяц
                other_date.strftime("%d.%m.%Y %H:%M:%S"),   # другой месяц
                target_date.strftime("%d.%m.%Y %H:%M:%S"),  # целевой месяц
            ],
            "Сумма платежа": [1000.0, 2000.0, 500.0],
            "Категория": ["Целевой", "Другой", "Целевой"],
            "Описание": ["Оп1", "Оп2", "Оп3"]
        }
        df = pd.DataFrame(data)
        df.to_excel(f.name, index=False)
        temp_path = f.name
    
    try:
        result = u.top_transactions_by_payment(temp_path, n=5, target_month=9, target_year=2025)
        # Должны остаться только транзакции целевого месяца
        assert len(result) == 2  # только 2 транзакции целевого месяца
        # Проверяем, что самая крупная транзакция - 1000.0 (целевой месяц)
        assert result[0]["amount"] == 1000.0
        assert result[1]["amount"] == 500.0
    finally:
        os.unlink(temp_path)
