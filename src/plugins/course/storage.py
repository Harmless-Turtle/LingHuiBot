from pathlib import Path

from ..utils import handle_json

DATA_DIR = Path.cwd() / "data" / "course"


def _schedule_path(user_id: str) -> Path:
    return DATA_DIR / f"{user_id}.json"


def save_schedule(user_id: str, data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    handle_json(_schedule_path(user_id), "w", data)


def load_schedule(user_id: str) -> dict | None:
    try:
        return handle_json(_schedule_path(user_id), "r")
    except FileNotFoundError:
        return None


def clear_schedule(user_id: str) -> None:
    path = _schedule_path(user_id)
    if path.exists():
        path.unlink(missing_ok=True)
