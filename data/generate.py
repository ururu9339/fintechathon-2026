from datetime import date, timedelta
from decimal import Decimal
import json
from pathlib import Path


def generate_seed(path: str = "data/seeds/demo_transactions.json") -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {"date": (date.today() - timedelta(days=7 * index)).isoformat(), "type": "sale", "amount": str(Decimal("4200"))}
        for index in range(13)
    ]
    target.write_text(json.dumps(rows, indent=2) + "\n")
    return target


if __name__ == "__main__":
    print(generate_seed())
