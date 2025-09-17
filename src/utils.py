from typing import List, Dict

import pandas as pd
import json
import requests
import os
from datetime import datetime

from config import PATH_TO_OPERATIONS, PATH_TO_USER_SETTINGS

def load_transactions_data(path: str) -> pd.DataFrame:
    """
    Читает XLS/XLSX.
    :param path: Указываем путь и название файла
    :return: Функция возвращает список словарей (records).
    """
    try:
        df = pd.read_excel(path)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"XLSX-файл не найден: {path}") from e
    except Exception as e:
        raise RuntimeError(f"Ошибка чтения XLS/XLSX: {path}") from e

    return df


def process_transactions(path: str):
    df = load_transactions_data(path)
    df["Номер карты"] = df["Номер карты"].astype(str)
    grouped_data = df.groupby("Номер карты").agg(
        Сумма_операций=("Сумма операции", "sum"),
        Кешбек=("Кэшбэк", "sum")
    ).reset_index()
    return grouped_data


def load_user_settings(path: str):
    """
    Загружает пользовательские настройки из JSON файла.
    
    Returns:
        Dict[str, Any]: Словарь с настройками пользователя
    """
    try:
        with open(path, encoding="utf-8") as file:
            data = json.load(file)

        # Проверяем, что файл содержит именно список объектов
        if isinstance(data, list):
            return data
        else:
            return []
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as e:
        return []

def get_currency_rates(currencies):
    """Получает курсы валют через API"""
    # Ваш код здесь

def get_stock_prices(stocks):
    """Получает цены акций через API"""
    # Ваш код здесь

def filter_by_date_range(transactions, start_date, end_date):
    """Фильтрует транзакции по датам"""
    # Ваш код здесь


if __name__ == "__main__": # pragma: no cover
    print(load_transactions_data(PATH_TO_OPERATIONS))
    print("____")
    print(load_user_settings(PATH_TO_USER_SETTINGS))