"""이전에 확인한 게시물 상태(data/seen_state.json)를 읽고 쓴다.

상태 구조:
{
  "<site_id>": {
    "<item_id>": {"title": "...", "date": "...", "hash": "...", "last_seen": "2026-07-01T09:00:00"}
  }
}
"""
import json
from pathlib import Path

DEFAULT_STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "seen_state.json"


def load_state(path: Path = DEFAULT_STATE_PATH) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict, path: Path = DEFAULT_STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
