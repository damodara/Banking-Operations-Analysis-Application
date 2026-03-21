import json
import logging
import re
from datetime import datetime
from typing import Dict, List

import pandas as pd

from src.utils import load_transactions_data

# Логирование для сервиса поиска по телефонным номерам
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


def get_mobile_transactions(path: str, target_month: int = None, target_year: int = None) -> List[Dict]:
    """
    Возвращает JSON со всеми транзакциями, содержащими в описании мобильные номера.

    Ищет транзакции, в описании которых есть мобильные номера в форматах:
    - +7 XXX XXX-XX-XX
    - +7 XXX XXX XX XX
    - +7XXXXXXXXXX
    - 8 XXX XXX-XX-XX
    - 8 XXX XXX XX XX
    - 8XXXXXXXXXX

    Args:
        path (str): Путь к Excel файлу с транзакциями
        target_month (int, optional): Номер месяца (1-12), если None - текущий месяц
        target_year (int, optional): Год, если None - текущий год

    Returns:
        List[Dict]: Список словарей с транзакциями, содержащими мобильные номера

    Example:
        >>> transactions = get_mobile_transactions("data/operations.xlsx", 9, 2021)
        >>> print(transactions)
        [
            {
                "date": "15.09.2021",
                "amount": -500.0,
                "description": "Я МТС +7 921 11-22-33",
                "category": "Связь"
            }
        ]
    """
    df = load_transactions_data(path)
    if df.empty or "Описание" not in df.columns:
        return []

    # Определяем месяц и год для фильтрации
    if target_month is None or target_year is None:
        current_date = datetime.now()
        target_month = target_month or current_date.month
        target_year = target_year or current_date.year

    # Фильтруем данные за указанный месяц
    if "Дата операции" in df.columns:
        df["Дата операции"] = pd.to_datetime(df["Дата операции"], dayfirst=True, errors="coerce")
        df = df.dropna(subset=["Дата операции"])
        df = df[(df["Дата операции"].dt.year == target_year) & (df["Дата операции"].dt.month == target_month)]

    if df.empty:
        return []

    # Регулярное выражение для поиска мобильных номеров
    mobile_pattern = r"(?:\+?7|8)(?:\s[0-9]{3}\s[0-9]{2}[\-][0-9]{2}[\-][0-9]{2}|\s[0-9]{3}\s[0-9]{3}[\-][0-9]{2}[\-][0-9]{2}|\s[0-9]{3}\s[0-9]{3}\s[0-9]{2}\s[0-9]{2}|[0-9]{10}|\([0-9]{3}\)[0-9]{3}[\-][0-9]{2}[\-][0-9]{2})"

    # Фильтруем транзакции с мобильными номерами в описании
    mobile_transactions = df[df["Описание"].str.contains(mobile_pattern, regex=True, na=False)]

    if mobile_transactions.empty:
        return []

    # Форматируем результат
    results = []
    for _, row in mobile_transactions.iterrows():
        # Форматируем дату
        date_str = ""
        if pd.notna(row.get("Дата операции")):
            if isinstance(row["Дата операции"], str):
                date_str = row["Дата операции"]
            else:
                date_str = row["Дата операции"].strftime("%d.%m.%Y")

        # Получаем сумму
        amount = 0.0
        if pd.notna(row.get("Сумма операции")):
            amount = float(row["Сумма операции"])

        # Получаем описание
        description = str(row.get("Описание", ""))

        # Получаем категорию
        category = str(row.get("Категория", ""))

        results.append({"date": date_str, "amount": amount, "description": description, "category": category})

    return results


def search_phone_transactions(transactions: List[Dict]) -> str:
    """
    Сервис «Поиск по телефонным номерам».

    Принимает список транзакций (словарей), находит записи, где в поле
    "Описание" присутствует мобильный номер телефона, и возвращает JSON
    с транзакциями в формате:
        [{"date": str, "amount": float, "description": str, "category": str}, ...]

    Использует библиотеки json, re, logging.

    Args:
        transactions (List[Dict]): Список транзакций (как словари), где
            ожидаются поля: "Дата операции", "Описание", "Сумма операции", "Категория".

    Returns:
        str: JSON-строка с найденными транзакциями.
    """
    logger.info("Запуск сервиса поиска по телефонным номерам в %d транзакциях", len(transactions))

    if not transactions:
        logger.info("Получен пустой список транзакций. Возвращаю пустой JSON-массив.")
        return json.dumps([], ensure_ascii=False)

    # Регулярное выражение должно совпадать с используемым в модуле
    mobile_pattern = r"(?:\+?7|8)(?:\s[0-9]{3}\s[0-9]{2}[\-][0-9]{2}[\-][0-9]{2}|\s[0-9]{3}\s[0-9]{3}[\-][0-9]{2}[\-][0-9]{2}|\s[0-9]{3}\s[0-9]{3}\s[0-9]{2}\s[0-9]{2}|[0-9]{10}|\([0-9]{3}\)[0-9]{3}[\-][0-9]{2}[\-][0-9]{2})"

    results: List[Dict] = []
    matched_count = 0
    for tx in transactions:
        description = str(tx.get("Описание", ""))
        if not description:
            continue
        if re.search(mobile_pattern, description):
            matched_count += 1
            # Дата
            date_raw = tx.get("Дата операции")
            date_str = ""
            if isinstance(date_raw, str):
                # Попытка нормализации формата дд.мм.гггг
                try:
                    # Возможные форматы строк: 'dd.mm.YYYY HH:MM:SS' или уже 'dd.mm.YYYY'
                    if len(date_raw) > 10 and ":" in date_raw:
                        from datetime import datetime as _dt

                        parsed = _dt.strptime(date_raw, "%d.%m.%Y %H:%M:%S")
                        date_str = parsed.strftime("%d.%m.%Y")
                    else:
                        date_str = date_raw
                except Exception:
                    date_str = date_raw
            else:
                # Если это datetime/ Timestamp
                try:
                    date_str = date_raw.strftime("%d.%m.%Y") if date_raw else ""
                except Exception:
                    date_str = ""

            amount_val = tx.get("Сумма операции")
            try:
                amount = float(amount_val) if amount_val is not None else 0.0
            except Exception:
                amount = 0.0

            results.append(
                {
                    "date": date_str,
                    "amount": amount,
                    "description": description,
                    "category": str(tx.get("Категория", "")),
                }
            )

    logger.info("Найдено %d транзакций с телефонными номерами", matched_count)
    return json.dumps(results, ensure_ascii=False)


def find_mobile_numbers_in_text(text: str) -> List[str]:
    """
    Находит все мобильные номера в тексте.

    Args:
        text (str): Текст для поиска

    Returns:
        List[str]: Список найденных мобильных номеров

    Example:
        >>> find_mobile_numbers_in_text("Я МТС +7 921 11-22-33 и Тинькофф Мобайл +7 995 555-55-55")
        ['+7 921 11-22-33', '+7 995 555-55-55']
    """
    if not text or not isinstance(text, str):
        return []

    mobile_pattern = r"(?:\+?7|8)(?:\s[0-9]{3}\s[0-9]{2}[\-][0-9]{2}[\-][0-9]{2}|\s[0-9]{3}\s[0-9]{3}[\-][0-9]{2}[\-][0-9]{2}|\s[0-9]{3}\s[0-9]{3}\s[0-9]{2}\s[0-9]{2}|[0-9]{10}|\([0-9]{3}\)[0-9]{3}[\-][0-9]{2}[\-][0-9]{2})"
    matches = re.findall(mobile_pattern, text)
    return matches
