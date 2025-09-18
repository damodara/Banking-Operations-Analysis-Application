import json
import logging
import os
from datetime import datetime

from config import PATH_TO_OPERATIONS, PATH_TO_USER_SETTINGS
from src.reports import spending_by_category
from src.services import get_mobile_transactions
from src.utils import (
    build_cards,
    get_currency_rates,
    get_stock_prices,
    load_transactions_data,
    load_user_settings,
    top_transactions_by_payment,
)
from src.views import greetings

# Инициализация логирования в файл и консоль
os.makedirs("logs", exist_ok=True)
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

# Всегда добавляем файловый хендлер (перезаписываем файл на каждый запуск)
fh = logging.FileHandler("logs/app.log", mode="w", encoding="utf-8")
fh.setFormatter(fmt)
root_logger.addHandler(fh)

# Консольный по необходимости, чтобы не плодить дубликаты
if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    root_logger.addHandler(ch)
import logging

logging.basicConfig(
    level=logging.INFO,
    filename="logs/app.log",
    filemode="a",
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

# Время для анализа
time_string = "2021-11-21 04:59:01"

# Извлекаем месяц и год из строки времени
parsed_time = datetime.strptime(time_string, "%Y-%m-%d %H:%M:%S")
target_month = parsed_time.month
target_year = parsed_time.year

# Приветствие
greeting_msg = greetings(time_string)

# Настройки пользователя
user_settings = load_user_settings(PATH_TO_USER_SETTINGS)
user_currencies = user_settings[0].get("user_currencies") if user_settings else ["USD", "EUR"]
user_stocks = user_settings[0].get("user_stocks") if user_settings else ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"]

# Групировка карт и транзакций за указанный месяц
cards = build_cards(PATH_TO_OPERATIONS, target_month, target_year)

# Мобильные транзакции
mobile_transactions = get_mobile_transactions(PATH_TO_OPERATIONS, target_month, target_year)

# Отчет «Траты по категории» (пример: Супермаркеты). Результат будет сохранен в reports/...
transactions_df = load_transactions_data(PATH_TO_OPERATIONS)
_ = spending_by_category(transactions_df, category="Супермаркеты", date=parsed_time.strftime("%Y-%m-%d"))

result = {
    "greeting": greeting_msg,
    "cards": cards,
    "top_transactions": top_transactions_by_payment(
        PATH_TO_OPERATIONS, n=5, target_month=target_month, target_year=target_year
    ),
    "mobile_transactions": mobile_transactions,
    "currency_rates": get_currency_rates(user_currencies),
    "stock_prices": get_stock_prices(user_stocks),
}

print(json.dumps(result, ensure_ascii=False, indent=4))
