from src.views import greetings
from tests.conftest import valid_time_string

def test_greetings(valid_time_string: str):
    for input_date, expected_result in valid_time_string:
        result = greetings(input_date)
        assert result == expected_result

