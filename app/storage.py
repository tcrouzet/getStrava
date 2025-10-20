import json
from pathlib import Path

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

def athlete_dir(athlete_id: int) -> Path:
    d = DATA_DIR / str(athlete_id)
    d.mkdir(parents=True, exist_ok=True)
    return d

def activities_json_path(athlete_id: int) -> Path:
    return athlete_dir(athlete_id) / "activities.json"


def load_existing_activities(athlete_id: int) -> list[dict]:
    p = activities_json_path(athlete_id)
    if not p.exists():
        return []
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_activities(athlete_id: int, activities: list[dict]) -> None:
    p = activities_json_path(athlete_id)
    tmp = p.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(activities, f, ensure_ascii=False, indent=2, default=str)
    tmp.replace(p)

def streams_dir(athlete_id: int) -> Path:
    d = athlete_dir(athlete_id) / "streams"
    d.mkdir(parents=True, exist_ok=True)
    return d

def stream_json_path(athlete_id: int, activity_id: int) -> Path:
    return streams_dir(athlete_id) / f"{activity_id}.json"

def save_streams(athlete_id: int, activity_id: int, streams: dict) -> None:
    p = stream_json_path(athlete_id, activity_id)
    tmp = p.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(streams, f, ensure_ascii=False, indent=2)
    tmp.replace(p)