import json
from datetime import datetime

from config import PATH_TO_OPERATIONS, PATH_TO_USER_SETTINGS
from src.utils import (
    build_cards,
    get_currency_rates,
    get_stock_prices,
    load_user_settings,
    top_transactions_by_payment,
)
from src.views import greetings

# Время для анализа
time_string = "2021-09-21 04:59:01"

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

result = {
    "greeting": greeting_msg,
    "cards": cards,
    "top_transactions": top_transactions_by_payment(PATH_TO_OPERATIONS, n=5, target_month=target_month, target_year=target_year),
    "currency_rates": get_currency_rates(user_currencies),
    "stock_prices": get_stock_prices(user_stocks),
}

print(json.dumps(result, ensure_ascii=False, indent=4))
