# app/auth.py


# from fastapi import APIRouter
# router = APIRouter()
# @router.get("/ping")
# def ping():
#     return {"pong": True}


import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse


# 1) Router défini immédiatement pour éviter tout échec d'import
router = APIRouter()

# 2) Logique OAuth/Strava ajoutée après (paresseuse)
import os
import time
from urllib.parse import urlencode
from typing import Dict, Any
from authlib.integrations.starlette_client import OAuth
from stravalib import Client as StravaClient
from .strava_client import set_token, persist_token

# Stockage en mémoire pour tests (remplace par une DB plus tard)
TOKENS: Dict[int, Dict[str, Any]] = {}

oauth = OAuth()

def ensure_strava_registered():
    """
    Enregistre le provider Strava au premier usage, avec variables d'env déjà chargées.
    Évite les erreurs d'import si les env ne sont pas encore disponibles.
    """
    if "strava" in oauth._clients:
        return

    cid = os.getenv("STRAVA_CLIENT_ID")
    secret = os.getenv("STRAVA_CLIENT_SECRET")
    redirect_uri = os.getenv("STRAVA_REDIRECT_URI")

    if not cid or not secret or not redirect_uri:
        raise HTTPException(
            status_code=500,
            detail="Config OAuth incomplète (STRAVA_CLIENT_ID/STRAVA_CLIENT_SECRET/STRAVA_REDIRECT_URI).",
        )

    oauth.register(
        name="strava",
        client_id=cid,
        client_secret=secret,
        access_token_url="https://www.strava.com/oauth/token",
        authorize_url="https://www.strava.com/oauth/authorize",
        client_kwargs={
            "scope": "read,activity:read_all",
            "token_endpoint_auth_method": "client_secret_post",
        },
    )

@router.get("/auth/strava/login")
async def strava_login(request: Request):
    cid = os.getenv("STRAVA_CLIENT_ID")
    redirect_uri = os.getenv("STRAVA_REDIRECT_URI")
    if not cid or not redirect_uri:
        raise HTTPException(status_code=500, detail="STRAVA_CLIENT_ID/STRAVA_REDIRECT_URI manquants.")
    params = {
        "client_id": cid,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "approval_prompt": "auto",
        "scope": "read,activity:read_all",
    }
    auth_url = f"https://www.strava.com/oauth/authorize?{urlencode(params)}"
    return RedirectResponse(auth_url)


@router.get("/auth/strava/callback")
async def strava_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing code")
    cid = os.getenv("STRAVA_CLIENT_ID")
    secret = os.getenv("STRAVA_CLIENT_SECRET")
    redirect_uri = os.getenv("STRAVA_REDIRECT_URI")

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            "https://www.strava.com/oauth/token",
            data={
                "client_id": cid,
                "client_secret": secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    token = resp.json()

    athlete = token.get("athlete") or {}
    athlete_id = athlete.get("id")
    if not athlete_id:
        raise HTTPException(status_code=400, detail="Athlete ID manquant")

    set_token(athlete_id, token)       # met en mémoire (pour cette exécution)
    persist_token(athlete_id, token)   # persiste sur disque (reprenable)

    TOKENS[athlete_id] = token
    return JSONResponse(
        {
            "status": "ok",
            "athlete_id": athlete_id,
            "expires_at": token.get("expires_at"),
            "scopes": token.get("scope"),
        }
    )



def get_stravalib_client(athlete_id: int) -> StravaClient:
    """
    Retourne un client stravalib avec access_token valide.
    Rafraîchit le token si nécessaire.
    """
    tok = TOKENS.get(athlete_id)
    if not tok:
        raise HTTPException(status_code=401, detail="Pas de session Strava pour cet athlete_id.")

    client = StravaClient(access_token=tok["access_token"])

    cid = os.getenv("STRAVA_CLIENT_ID") or ""
    secret = os.getenv("STRAVA_CLIENT_SECRET") or ""

    # Rafraîchir si proche de l'expiration (marge 60s)
    if time.time() >= tok.get("expires_at", 0) - 60:
        new_tok = client.refresh_access_token(
            client_id=cid,
            client_secret=secret,
            refresh_token=tok["refresh_token"],
        )
        tok.update(new_tok)
        TOKENS[athlete_id] = tok
        client.access_token = tok["access_token"]

    return client

@router.get("/auth/strava/token")
def get_token(athlete_id: int):
    """
    Endpoint de debug: visualiser l'état du token pour un athlete_id.
    """
    tok = TOKENS.get(athlete_id)
    if not tok:
        raise HTTPException(status_code=404, detail="Aucun token pour cet athlete_id.")
    return {
        "athlete_id": athlete_id,
        "expires_at": tok.get("expires_at"),
        "has_refresh_token": bool(tok.get("refresh_token")),
        "scopes": tok.get("scope"),
    }

