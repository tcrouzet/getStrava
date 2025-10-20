import os, time
from fastapi import HTTPException
from stravalib import Client as StravaClient
from pathlib import Path
import json

TOKENS_DIR = Path("data/tokens")
TOKENS_DIR.mkdir(parents=True, exist_ok=True)
TOKENS = {}  # on le gardera ici ou on l’injectera depuis auth

def set_token(athlete_id: int, token: dict):
    TOKENS[athlete_id] = token

def get_token(athlete_id: int) -> dict | None:
    return TOKENS.get(athlete_id)

# def get_stravalib_client(athlete_id: int) -> StravaClient:
#     tok = TOKENS.get(athlete_id)
#     if not tok:
#         raise HTTPException(status_code=401, detail="Pas de session Strava.")
#     client = StravaClient(access_token=tok["access_token"])
#     cid = os.getenv("STRAVA_CLIENT_ID") or ""
#     secret = os.getenv("STRAVA_CLIENT_SECRET") or ""
#     if time.time() >= tok.get("expires_at", 0) - 60:
#         new_tok = client.refresh_access_token(
#             client_id=cid, client_secret=secret, refresh_token=tok["refresh_token"]
#         )
#         tok.update(new_tok)
#         TOKENS[athlete_id] = tok
#         client.access_token = tok["access_token"]
#     return client


def get_stravalib_client(athlete_id: int) -> StravaClient:
    tok = TOKENS.get(athlete_id)
    if not tok:
        tok = load_persisted_token(athlete_id)
        if tok:
            TOKENS[athlete_id] = tok
    if not tok:
        raise HTTPException(status_code=401, detail="Pas de session Strava.")

    client = StravaClient(access_token=tok["access_token"])
    # Donne le refresh_token au client pour éviter le warning
    if tok.get("refresh_token"):
        client.refresh_token = tok["refresh_token"]

    cid = os.getenv("STRAVA_CLIENT_ID") or ""
    secret = os.getenv("STRAVA_CLIENT_SECRET") or ""

    # Rafraîchit pro-activement si proche de l’expiration (marge 60s)
    if time.time() >= tok.get("expires_at", 0) - 60:
        new_tok = client.refresh_access_token(
            client_id=cid,
            client_secret=secret,
            refresh_token=tok["refresh_token"],
        )
        tok.update(new_tok)
        TOKENS[athlete_id] = tok
        persist_token(athlete_id, tok)  # pense à persister la mise à jour
        client.access_token = tok["access_token"]
        if tok.get("refresh_token"):
            client.refresh_token = tok["refresh_token"]

    return client

def _token_path(athlete_id: int) -> Path:
    return TOKENS_DIR / f"token_{athlete_id}.json"

def persist_token(athlete_id: int, token: dict):
    p = _token_path(athlete_id)
    tmp = p.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(token, f, ensure_ascii=False, indent=2)
    tmp.replace(p)

def load_persisted_token(athlete_id: int) -> dict | None:
    p = _token_path(athlete_id)
    if not p.exists():
        return None
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None