import json
from datetime import datetime


def greetings(time_string: str) -> str:
    """
    Сообщение приветствия на основе полученного времени
    :param time_string: Дата в формате datetime, а именно YYYY-MM-DD HH:MM:SS
    :return: Строка с приветствием
    """
    try:
        welcome_msg = ""
        parsed_time = datetime.strptime(time_string, "%Y-%m-%d %H:%M:%S")
        hour = parsed_time.hour
        if 5 <= hour < 12:
            welcome_msg = "Доброе утро"
        elif 12 <= hour < 18:
            welcome_msg = "Добрый день"
        elif 18 <= hour < 23:
            welcome_msg = "Добрый вечер"
        else:
            welcome_msg = "Доброй ночи"
    except ValueError:
        welcome_msg = "Неверный формат времени"

    return welcome_msg


if __name__ == "__main__":  # pragma: no cover
    print(greetings("2025-09-21 04:59:01"))
