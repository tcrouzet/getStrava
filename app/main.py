# app/main.py
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
import os

from .auth import router
from .activities import router as activities_router

app = FastAPI()

SESSION_SECRET = os.getenv("SESSION_SECRET", "devsecret")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

@app.get("/health")
def health():
    return {"ok": True}

app.include_router(router)
app.include_router(activities_router)
