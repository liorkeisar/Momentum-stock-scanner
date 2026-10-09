import json
import os

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchlist.json")


def load():
    try:
        with open(PATH, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save(data):
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
