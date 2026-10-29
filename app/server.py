"""Petit serveur FastAPI : n8n (Schedule) appelle POST /run-reminders chaque matin.
Lancer : uvicorn app.server:api --port 8000"""
import os
from fastapi import FastAPI, Header, HTTPException
from . import notifier
api = FastAPI(title="JobPilot reminders")

@api.get("/health")
def health(): return {"ok": True}

@api.post("/run-reminders")
def run(x_token: str = Header(None)):
    if not os.getenv("CRON_TOKEN") or x_token != os.getenv("CRON_TOKEN"):
        raise HTTPException(401, "Token invalide")
    return {"notifications": notifier.run_all()}
