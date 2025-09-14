from datetime import datetime
def greetings(time_string):
    """
    Сообщение приветствия на основе полученного времени
    :param time_string: Дата в формате datetime, а именно YYYY-MM-DD HH:MM:SS
    :return: Строка с приветствием
    """
    try:
        parsed_time = datetime.strptime(time_string, "%Y-%m-%d %H:%M:%S")
        hour = parsed_time.hour
        if 5 <= hour < 12:
            return "Доброе утро"
        elif 12 <= hour < 18:
            return "Добрый день"
        elif 18 <= hour < 23:
            return "Добрый вечер"
        else:
            return "Доброй ночи"
    except ValueError:
        return "Неверный формат времени"


if __name__ == "__main__": # pragma: no cover
    print(greetings("2025-09-21 04:59:01"))
