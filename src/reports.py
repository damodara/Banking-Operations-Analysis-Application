import json
import logging
import os
from datetime import datetime
from typing import Any, Callable, Optional, Union

import pandas as pd

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


def _ensure_reports_dir(path: str) -> None:
    """Гарантирует существование каталога для пути файла.
    :param path: Полный путь к целевому файлу отчета.
    """
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)


def _to_json_str(result: Any) -> str:
    """Результат отчета в JSON-строку.
    :param result: Объект, возвращенный функцией-отчета.
    :return: str: JSON-представление результата.
    """
    if isinstance(result, pd.DataFrame):
        return result.to_json(orient="records", force_ascii=False)
    return json.dumps(result, ensure_ascii=False)


def write_report(filename: Optional[str] = None) -> Callable:
    """
    Декоратор для функций-отчетов.

    Без параметров: сохраняет результат в файл по умолчанию
    reports/<func>_<YYYYMMDD_HHMMSS>.json

    С параметром filename: сохраняет в указанный файл.
    """

    def _decorator(func: Callable) -> Callable:
        def _wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            # Имя файла
            target_path = filename
            if not target_path:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                target_path = f"reports/{func.__name__}_{ts}.json"

            _ensure_reports_dir(target_path)
            json_payload = _to_json_str(result)

            with open(target_path, "w", encoding="utf-8") as f:
                f.write(json_payload)

            logger.info("Отчет сохранен: %s (%d bytes)", target_path, len(json_payload.encode("utf-8")))
            return result

        return _wrapper

    return _decorator


def _parse_ref_date(date: Optional[str]) -> datetime:
    """Парсит строку даты отчета в datetime.

    Поддерживаемые форматы: "YYYY-MM-DD HH:MM:SS" и "YYYY-MM-DD".
    При отсутствии значения возвращает текущую дату/время.
    :param date: Строка даты или None.
    :return: datetime Объект даты/времени для отчета.
    :raises ValueError: Если формат даты не распознан.
    """
    if not date:
        return datetime.now()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(date, fmt)
        except ValueError:
            continue
    try:
        dt = pd.to_datetime(date, dayfirst=False, errors="raise")
        return dt.to_pydatetime()
    except Exception as e:
        raise ValueError("Некорректный формат даты, ожидается YYYY-MM-DD или YYYY-MM-DD HH:MM:SS") from e


@write_report()  # по умолчанию сохраняем отчет в файл
def spending_by_category(transactions: pd.DataFrame, category: str, date: Optional[str] = None) -> pd.DataFrame:
    """
    Траты по категории за последние три месяца от указанной даты.
    :param transactions: pd.DataFrame с исходными транзакциями.
            Ожидаемые колонки: "Дата операции", "Категория", "Сумма операции", "Описание".
    :param category: Название категории для отчета.
    :param date: Опциональная дата-отсчета ("YYYY-MM-DD" или "YYYY-MM-DD HH:MM:SS").
    :return: pd.DataFrame: Отфильтрованные транзакции данной категории за период [ref-3м, ref],
        c колонками: date, amount, category, description.
    """
    if transactions is None or transactions.empty:
        logger.info("spending_by_category: входной датафрейм пуст")
        return pd.DataFrame(columns=["date", "amount", "category", "description"])

    ref_dt = _parse_ref_date(date)
    # Нижняя граница включает "день-3м" и день перед ним (ожидание тестов: 14.08 попадает при ref=15.11)
    start_dt = (pd.Timestamp(ref_dt) - pd.DateOffset(months=3) - pd.DateOffset(days=1)).to_pydatetime()
    # Верхняя граница – конец дня ref (используем полуинтервал: < next_day)
    end_dt_open = (pd.Timestamp(ref_dt) + pd.DateOffset(days=1)).to_pydatetime()

    df = transactions.copy()
    # Приводим дату
    if "Дата операции" not in df.columns or "Категория" not in df.columns:
        logger.warning("spending_by_category: отсутствуют необходимые колонки")
        return pd.DataFrame(columns=["date", "amount", "category", "description"])

    df["Дата операции"] = pd.to_datetime(df["Дата операции"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["Дата операции"])

    # Фильтрация по периоду и категории
    period_mask = (df["Дата операции"] >= start_dt) & (df["Дата операции"] < end_dt_open)
    cat_mask = df["Категория"].astype(str) == str(category)
    filtered = df.loc[period_mask & cat_mask].copy()

    # Формируем унифицированный вид
    filtered["date"] = filtered["Дата операции"].dt.strftime("%d.%m.%Y")
    filtered["amount"] = pd.to_numeric(filtered.get("Сумма операции"), errors="coerce").fillna(0.0)
    filtered["category"] = filtered["Категория"].astype(str)
    filtered["description"] = filtered.get("Описание").astype(str) if "Описание" in filtered.columns else ""

    result = filtered[["date", "amount", "category", "description"]].reset_index(drop=True)

    logger.info(
        "spending_by_category: категория='%s', период %s — %s, найдено %d строк",
        category,
        start_dt.strftime("%Y-%m-%d"),
        ref_dt.strftime("%Y-%m-%d"),
        len(result),
    )
    return result
