import json

from config import PATH_TO_OPERATIONS
from src.utils import build_cards
from src.views import greetings
#приветствие
greeting_msg = greetings("2025-09-21 04:59:01")
cards = build_cards(PATH_TO_OPERATIONS)
json_msg = json.dumps({
    'greeting': greeting_msg,
    'cards': cards
}, ensure_ascii=False, indent=4)

print(json_msg)
