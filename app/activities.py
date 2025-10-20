from typing import Iterator
from fastapi import APIRouter
from fastapi import HTTPException
from time import sleep
import json
from .strava_client import get_stravalib_client
from .storage import load_existing_activities, save_activities, activities_json_path, stream_json_path, save_streams, streams_dir

router = APIRouter()

ALL_STREAM_KEYS = [
    "time", "distance", "latlng", "altitude",
    "velocity_smooth", "heartrate", "cadence", "watts",
    "temp", "grade_smooth", "moving",
]

DEFAULT_STREAM_KEYS = [
    "time", "latlng", "altitude", "heartrate", "cadence", "watts"
]

def iter_all_activities(client, batch_size: int = 200) -> Iterator:
    offset = 0
    last_len = 0
    while True:
        curr = list(client.get_activities(limit=offset + batch_size))
        if len(curr) <= last_len:
            break
        new_slice = curr[offset : offset + batch_size]
        if not new_slice:
            break
        for a in new_slice:
            yield a
        last_len = len(curr)
        offset += batch_size

def normalize_activity(a) -> dict:
    d = a.model_dump()
    return {
        "id": d.get("id"),
        "name": d.get("name"),
        "sport_type": d.get("sport_type") or d.get("type"),
        "start_date": d.get("start_date"),
        "distance": d.get("distance"),
        "moving_time": d.get("moving_time"),
        "elapsed_time": d.get("elapsed_time"),
        "total_elevation_gain": d.get("total_elevation_gain"),
        "private": d.get("private"),
    }

@router.api_route("/strava/export_activities", methods=["GET", "POST"])
def export_activities_json(
    athlete_id: int,
    batch_size: int = 200,
    sleep_ms: int = 0,
    max_new: int | None = None,
):
    client = get_stravalib_client(athlete_id)
    existing = load_existing_activities(athlete_id)
    known_ids = {a.get("id") for a in existing if "id" in a}
    added, buffer = 0, []

    for act in iter_all_activities(client, batch_size=batch_size):
        aid = getattr(act, "id", None)
        if not aid or aid in known_ids:
            continue
        buffer.append(normalize_activity(act))
        known_ids.add(aid)
        added += 1

        if len(buffer) >= 100:
            existing.extend(buffer)
            save_activities(athlete_id, existing)
            buffer.clear()

        if max_new and added >= max_new:
            break
        if sleep_ms > 0:
            sleep(sleep_ms / 1000.0)

    if buffer:
        existing.extend(buffer)
        save_activities(athlete_id, existing)

    return {
        "athlete_id": athlete_id,
        "added": added,
        "total_in_file": len(existing),
        "file": str(activities_json_path(athlete_id)),
    }




@router.get("/strava/activities")
def list_activities(athlete_id: int, page: int = 1, per_page: int = 30):
    client = get_stravalib_client(athlete_id)

    total_to_fetch = max(per_page * page, per_page)
    acts_iter = client.get_activities(limit=total_to_fetch)
    acts_list = list(acts_iter)

    start = per_page * (page - 1)
    end = start + per_page
    slice_list = acts_list[start:end]

    # Résumé allégé
    out = []
    for a in slice_list:
        d = a.model_dump()
        out.append({
            "id": d.get("id"),
            "name": d.get("name"),
            "type": d.get("sport_type") or d.get("type"),
            "start_date": d.get("start_date"),
            "distance": d.get("distance"),         # en mètres
            "moving_time": d.get("moving_time"),   # en secondes
            "elapsed_time": d.get("elapsed_time"),
            "total_elevation_gain": d.get("total_elevation_gain"),
            "average_speed": d.get("average_speed"),
            "max_speed": d.get("max_speed"),
            "private": d.get("private"),
        })
    return out


# @router.api_route("/strava/export_streams", methods=["GET", "POST"])
# def export_all_streams(
#     athlete_id: int,
#     sleep_ms: int = 500,
#     keys: str = ",".join(ALL_STREAM_KEYS),
#     max_count: int | None = None,
#     force: bool = False,
# ):
#     acts_path = activities_json_path(athlete_id)
#     if not acts_path.exists():
#         raise HTTPException(status_code=400, detail=f"Catalogue introuvable: {acts_path}")

#     activities = json.loads(acts_path.read_text(encoding="utf-8"))

#     # with acts_path.open("r", encoding="utf-8") as f:
#     #     activities = json.load(f)

#     client = get_stravalib_client(athlete_id)
#     keys_list = [k.strip() for k in keys.split(",") if k.strip()]

#     processed = skipped = errors = 0

#     for a in activities:
#         aid = a.get("id")
#         if not aid:
#             continue

#         p = stream_json_path(athlete_id, aid)
#         if (not force) and p.exists():
#             skipped += 1
#             continue

#         try:
#             streams = fetch_activity_streams(client, aid, keys=keys_list)
#             save_streams(athlete_id, aid, streams)
#             processed += 1
#         except Exception as e:
#             errors += 1
#             print(f"[streams] erreur activity_id={aid}: {e}")

#         if max_count and processed >= max_count:
#             break
#         if sleep_ms > 0:
#             from time import sleep
#             sleep(sleep_ms / 1000.0)

#         break

#     return {
#         "athlete_id": athlete_id,
#         "processed": processed,
#         "skipped_existing": skipped,
#         "errors": errors,
#         "dir": str(streams_dir(athlete_id)),
#     }


@router.api_route("/strava/export_streams", methods=["GET", "POST"])
def export_all_streams(
    athlete_id: int,
    sleep_ms: int = 500,
    keys: str = ",".join(ALL_STREAM_KEYS),
    max_count: int | None = None,
    force: bool = False,
    series_type: str = "time",
    resolution: str = "high",
):

    # max_count = 1

    acts_path = activities_json_path(athlete_id)
    if not acts_path.exists():
        raise HTTPException(status_code=400, detail=f"Catalogue introuvable: {acts_path}")
    
    activities = json.loads(acts_path.read_text(encoding="utf-8"))

    client = get_stravalib_client(athlete_id)

    keys_list = [k.strip() for k in keys.split(",") if k.strip()]

    processed = skipped = errors = 0
    for a in activities:
        aid = a.get("id")
        if not aid:
            continue

        p = stream_json_path(athlete_id, aid)
        if (not force) and p.exists():
            skipped += 1
            continue

        try:
            streams = client.get_activity_streams(
                activity_id=aid,
                types=keys_list,
                series_type=series_type,
                resolution=resolution,
            )
            simple = {k: (v.data if hasattr(v, "data") else v) for k, v in streams.items()}
            save_streams(athlete_id, aid, simple)
            processed += 1
        except Exception as e:
            errors += 1
            print(f"[streams] erreur activity_id={aid}: {e}")

        if max_count and processed >= max_count:
            break
        if sleep_ms > 0:
            from time import sleep
            sleep(sleep_ms / 1000.0)

    return {
        "athlete_id": athlete_id,
        "processed": processed,
        "skipped_existing": skipped,
        "errors": errors,
        "dir": str(streams_dir(athlete_id)),
    }