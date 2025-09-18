import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import requests
from dotenv import load_dotenv

from config import PATH_TO_OPERATIONS, PATH_TO_USER_SETTINGS

# Логирование модуля utils
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


def load_transactions_data(path: Path) -> pd.DataFrame:
    """
    Читает XLS/XLSX.
    :param path: Указываем путь и название файла
    :return: Функция возвращает список словарей (records).
    """
    logger.info("Чтение XLSX: %s", path)
    try:
        df = pd.read_excel(path)
    except FileNotFoundError as e:
        logger.error("Файл не найден: %s", path)
        raise FileNotFoundError(f"XLSX-файл не найден: {path}") from e
    except Exception as e:
        logger.exception("Ошибка чтения XLS/XLSX: %s", path)
        raise RuntimeError(f"Ошибка чтения XLS/XLSX: {path}") from e

    return df


def process_transactions(path: str, target_month: int = None, target_year: int = None) -> pd.DataFrame:
    """
    Возвращает данные о транзакциях по картам за указанный месяц.
    :param path: путь к XLSX с операциями
    :param target_month: номер месяца (1-12), если None - текущий месяц
    :param target_year: год, если None - текущий год
    :return: pd.DataFrame
    """
    logger.info("Обработка транзакций (группировка по картам) для файла: %s", path)
    df = load_transactions_data(path)
    if df.empty or "Номер карты" not in df.columns:
        return pd.DataFrame(columns=["Номер карты", "Сумма_операций", "Кешбек"])

    # Определяем месяц и год для фильтрации
    if target_month is None or target_year is None:
        current_date = datetime.now()
        target_month = target_month or current_date.month
        target_year = target_year or current_date.year

    if "Дата операции" in df.columns:
        df["Дата операции"] = pd.to_datetime(df["Дата операции"], dayfirst=True, errors="coerce")
        df = df.dropna(subset=["Дата операции"])
        df = df[(df["Дата операции"].dt.year == target_year) & (df["Дата операции"].dt.month == target_month)]
        logger.info("Топ-платежи: фильтрация по %02d.%04d -> %d строк", target_month, target_year, len(df))
        logger.info("Фильтрация по периоду %02d.%04d -> %d строк", target_month, target_year, len(df))

    if df.empty:
        return pd.DataFrame(columns=["Номер карты", "Сумма_операций", "Кешбек"])

    df["Номер карты"] = df["Номер карты"].astype(str)
    grouped_data = (
        df.groupby("Номер карты").agg(Сумма_операций=("Сумма операции", "sum"), Кешбек=("Кэшбэк", "sum")).reset_index()
    )
    return grouped_data


def build_cards(path: str, target_month: int = None, target_year: int = None) -> List[Dict]:
    """
    Возвращает список словарей по всем картам с полями last_digits, total_spent, cashback.
    :param path: путь к XLSX с операциями
    :param target_month: номер месяца (1-12), если None - текущий месяц
    :param target_year: год, если None - текущий год
    :return: List[Dict]
    """
    df_grouped = process_transactions(path, target_month, target_year)
    cards = []
    if not df_grouped.empty:
        for _, row in df_grouped.iterrows():
            card_number = str(row.get("Номер карты", ""))
            total_raw = float(row.get("Сумма_операций", 0.0))
            cashback_raw = row.get("Кешбек", 0.0)
            cashback_val = float(cashback_raw) if pd.notna(cashback_raw) else 0.0
            cards.append(
                {
                    "last_digits": card_number[-4:] if card_number else "",
                    "total_spent": round(abs(total_raw), 2),
                    "cashback": round(cashback_val, 2),
                }
            )
    return cards


def top_transactions_by_payment(
    path: str, n: int = 5, target_month: int = None, target_year: int = None
) -> List[Dict]:
    """
    Возвращает топ-n транзакций по абсолютному значению поля "Сумма платежа" за указанный месяц.
    :param path: путь к XLSX с операциями
    :param n: количество транзакций
    :param target_month: номер месяца (1-12), если None - текущий месяц
    :param target_year: год, если None - текущий год
    :return: List[Dict]
    """
    df = load_transactions_data(path)
    if df.empty or "Сумма платежа" not in df.columns:
        return []

    # Определяем месяц и год для фильтрации
    if target_month is None or target_year is None:
        current_date = datetime.now()
        target_month = target_month or current_date.month
        target_year = target_year or current_date.year

    if "Дата операции" in df.columns:
        df["Дата операции"] = pd.to_datetime(df["Дата операции"], dayfirst=True, errors="coerce")
        df = df.dropna(subset=["Дата операции"])
        df = df[(df["Дата операции"].dt.year == target_year) & (df["Дата операции"].dt.month == target_month)]

    if df.empty:
        return []

    df["Сумма платежа"] = pd.to_numeric(df.get("Сумма платежа"), errors="coerce")
    df["Валюта платежа"] = df.get("Валюта платежа")
    df["Номер карты"] = df.get("Номер карты").astype(str) if df.get("Номер карты") is not None else ""
    df["Дата платежа"] = df.get("Дата платежа")

    df = df.dropna(subset=["Сумма платежа"])
    if df.empty:
        return []

    df_sorted = df.reindex(df["Сумма платежа"].abs().sort_values(ascending=False).index)
    top = df_sorted.head(n)

    results: List[Dict] = []
    for _, row in top.iterrows():
        raw_date = row.get("Дата платежа", "")
        date_str = raw_date.strftime("%d.%m.%Y") if isinstance(raw_date, datetime) else str(raw_date)
        amount = float(row.get("Сумма платежа", 0.0))
        results.append(
            {
                "date": date_str,
                "amount": round(amount, 2),
                "category": row.get("Категория", ""),
                "description": row.get("Описание", ""),
            }
        )

    return results


def get_currency_rates(
    currencies: List[str], to_currency: str = "RUB", use_static_fallback: bool = True
) -> List[Dict[str, Any]]:
    """
    Возвращает курсы указанных валют к валюте `to_currency` через apilayer.
    Делает один запрос к /latest и вычисляет кросс-курс (устойчиво к free-тарифу с фиксированной базой EUR).
    """
    logger.info("Получение курсов валют для: %s -> %s", ",".join(currencies), to_currency)
    load_dotenv()
    api_token = os.getenv("API_KEY")

    def _compute_rates_from_map(rates_map: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Вычисляет курсы указанных валют к валюте `to_currency` через apilayer.
        """
        results_local: List[Dict[str, Any]] = []
        to_val = rates_map.get(to_currency)
        to_num = float(to_val) if to_val is not None else None
        for cur in currencies:
            cur_val = rates_map.get(cur)
            if to_num is None or cur_val is None:
                results_local.append({"currency": cur, "rate": None})
                continue
            cur_num = float(cur_val)
            rate_val = to_num / cur_num if cur_num != 0 else None
            results_local.append({"currency": cur, "rate": round(rate_val, 2) if rate_val is not None else None})
        return results_local

    symbols_set = set([to_currency] + currencies)
    symbols = ",".join(sorted(symbols_set))

    if api_token:
        headers = {"apikey": api_token}
        try:
            url = f"https://api.apilayer.com/exchangerates_data/latest?symbols={symbols}"
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            rates_map = data.get("rates", {}) or {}
            results = _compute_rates_from_map(rates_map)
            if any(item["rate"] is not None for item in results):
                logger.info("Курсы получены от apilayer")
                return results
        except Exception:
            logger.warning("Ошибка получения курсов от apilayer, используем фолбэк", exc_info=True)

    # Если нет API_KEY или запрос не удался, используем статический фолбэк
    if use_static_fallback:
        static_rates: Dict[str, float] = {"USD": 73.21, "EUR": 87.08}
        result_static: List[Dict[str, Any]] = []
        for cur in currencies:
            rate_val = static_rates.get(cur)
            result_static.append({"currency": cur, "rate": round(rate_val, 2) if rate_val is not None else None})
        logger.info("Возврат статических курсов (фолбэк)")
        return result_static

    return [{"currency": cur, "rate": None} for cur in currencies]


def load_user_settings(path: Path) -> List[str]:
    """
    Загружает пользовательские настройки из JSON файла.
    :returns: Dict[str, Any]: Словарь с настройками пользователя
    """
    logger.info("Загрузка пользовательских настроек: %s", path)
    try:
        with open(path, encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            return data
        else:
            return []
    except FileNotFoundError:
        logger.warning("Файл настроек не найден: %s", path)
        return []
    except json.JSONDecodeError as e:
        logger.warning("Ошибка JSON в файле настроек: %s", path)
        return []


def get_stock_prices(tickers: List[str]) -> List[Dict[str, Any]]:
    """
    Возвращает текущие цены акций для заданных тикеров.
    Источник: stooq
    """
    logger.info("Получение цен акций: %s (stooq)", ",".join(tickers))
    try:
        if tickers:
            stooq_symbols = ",".join([f"{t.lower()}.us" for t in tickers])
            url = f"https://stooq.com/q/l/?s={stooq_symbols}&f=sd2t2ohlcv&h&e=csv"
            df = pd.read_csv(url)
            results: List[Dict[str, Any]] = []
            for t in tickers:
                row = df[df["Symbol"].str.lower().eq(f"{t.lower()}.us")]
                price = None
                if not row.empty and "Close" in row.columns:
                    try:
                        price = float(row.iloc[0]["Close"]) if pd.notna(row.iloc[0]["Close"]) else None
                    except Exception:
                        price = None
                results.append({"stock": t, "price": round(price, 2) if price is not None else None})
            if any(item["price"] is not None for item in results):
                logger.info("Цены акций получены от stooq")
                return results
    except Exception:
        logger.warning("Ошибка получения цен акций, возвращаю None", exc_info=True)

    return [{"stock": t, "price": None} for t in tickers]


if __name__ == "__main__":  # pragma: no cover
    print(load_transactions_data(PATH_TO_OPERATIONS))
    print("____")
    print(load_user_settings(PATH_TO_USER_SETTINGS))
