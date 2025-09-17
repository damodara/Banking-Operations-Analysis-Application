import json

from config import PATH_TO_OPERATIONS
from src.utils import process_transactions
from src.views import greetings
#приветствие
greeting_msg = greetings("2025-09-21 04:59:01")
#групировка карт и транзакций
df_grouped = process_transactions(PATH_TO_OPERATIONS)
cards = []
if not df_grouped.empty:
    for _, row in df_grouped.iterrows():
        card_number = str(row["Номер карты"]) if "Номер карты" in row else ""
        total_raw = float(row["Сумма_операций"]) if "Сумма_операций" in row else 0.0
        cashback_raw = row["Кешбек"] if "Кешбек" in row else 0.0
        cashback_val = float(cashback_raw) if cashback_raw == cashback_raw else 0.0  # NaN check
        cards.append({
            "last_digits": card_number[-4:] if card_number else "",
            "total_spent": round(abs(total_raw), 2),
            "cashback": round(cashback_val, 2)
        })
else:
    cards.append({
        "last_digits": "",
        "total_spent": 0.0,
        "cashback": 0.0
    })
json_msg = json.dumps({
    'greeting': greeting_msg,
    'cards': cards
}, ensure_ascii=False, indent=4)

print(json_msg)
