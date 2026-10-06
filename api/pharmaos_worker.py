from __future__ import annotations

import hashlib
import json
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from pymongo import ReturnDocument

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.core.mongo import get_db

app = FastAPI(title="MABRIG PharmaOS Compute Worker Bridge", version="1.0.0")

MAX_RESULT_BYTES = 256_000
DEFAULT_LEASE_SECONDS = 900
MAX_LEASE_SECONDS = 3600


class WorkerAction(BaseModel):
    action: str
    worker_id: str | None = Field(default=None, max_length=120)
    job_id: str | None = Field(default=None, max_length=120)
    result: dict[str, Any] | None = None
    error: str | None = Field(default=None, max_length=4000)
    lease_seconds: int = Field(default=DEFAULT_LEASE_SECONDS, ge=60, le=MAX_LEASE_SECONDS)


def now() -> datetime:
    return datetime.now(timezone.utc)


def require_worker(request: Request, body: WorkerAction) -> str:
    expected = settings.PHARMAOS_WORKER_TOKEN.strip()
    supplied = request.headers.get("x-pharmaos-worker-token", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="PharmaOS worker bridge is not configured")
    if not supplied or not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Invalid worker token")
    worker_id = (body.worker_id or request.headers.get("x-pharmaos-worker-id") or "").strip()
    if not worker_id:
        raise HTTPException(status_code=422, detail="worker_id is required")
    return worker_id[:120]


def public_job(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(doc.get("_id")),
        "title": doc.get("title"),
        "status": doc.get("status"),
        "manifest": doc.get("manifest"),
        "created_at": doc.get("created_at").isoformat() if isinstance(doc.get("created_at"), datetime) else doc.get("created_at"),
        "claimed_at": doc.get("claimed_at").isoformat() if isinstance(doc.get("claimed_at"), datetime) else doc.get("claimed_at"),
        "lease_expires_at": doc.get("lease_expires_at").isoformat() if isinstance(doc.get("lease_expires_at"), datetime) else doc.get("lease_expires_at"),
    }


def checked_result(result: dict[str, Any] | None) -> tuple[dict[str, Any], str]:
    payload = result or {}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    if len(raw) > MAX_RESULT_BYTES:
        raise HTTPException(status_code=413, detail=f"Result exceeds {MAX_RESULT_BYTES} byte limit; store large artifacts externally and submit references")
    return payload, hashlib.sha256(raw).hexdigest()


@app.get("/api/pharmaos_worker")
def worker_info():
    return {
        "name": "MABRIG PharmaOS Compute Worker Bridge",
        "protocol": "claim -> heartbeat -> complete|fail",
        "engine_target": "Kaggle AutoDock Vina / Meeko / RDKit worker",
        "authentication": "X-PharmaOS-Worker-Token",
    }


@app.post("/api/pharmaos_worker")
def worker_action(body: WorkerAction, request: Request):
    worker_id = require_worker(request, body)
    db = get_db()
    timestamp = now()

    if body.action == "claim":
        lease_expires_at = timestamp + timedelta(seconds=body.lease_seconds)
        job = db.discovery_screening_jobs.find_one_and_update(
            {
                "$or": [
                    {"status": "ready_for_worker"},
                    {"status": "running", "lease_expires_at": {"$lt": timestamp}},
                ]
            },
            {
                "$set": {
                    "status": "running",
                    "worker_id": worker_id,
                    "claimed_at": timestamp,
                    "lease_expires_at": lease_expires_at,
                    "updated_at": timestamp,
                },
                "$inc": {"worker_attempts": 1},
            },
            sort=[("created_at", 1)],
            return_document=ReturnDocument.AFTER,
        )
        if not job:
            return {"job": None, "message": "No screening jobs are waiting"}
        return {"job": public_job(job)}

    if body.action == "heartbeat":
        if not body.job_id:
            raise HTTPException(status_code=422, detail="job_id is required")
        lease_expires_at = timestamp + timedelta(seconds=body.lease_seconds)
        updated = db.discovery_screening_jobs.update_one(
            {"_id": body.job_id, "status": "running", "worker_id": worker_id},
            {"$set": {"lease_expires_at": lease_expires_at, "worker_heartbeat_at": timestamp, "updated_at": timestamp}},
        )
        if updated.matched_count != 1:
            raise HTTPException(status_code=409, detail="Job is not leased to this worker")
        return {"ok": True, "lease_expires_at": lease_expires_at.isoformat()}

    if body.action == "complete":
        if not body.job_id:
            raise HTTPException(status_code=422, detail="job_id is required")
        result, digest = checked_result(body.result)
        evidence_id = f"EVD-{body.job_id}"
        job = db.discovery_screening_jobs.find_one({"_id": body.job_id, "status": "running", "worker_id": worker_id})
        if not job:
            raise HTTPException(status_code=409, detail="Job is not leased to this worker")

        evidence = {
            "_id": evidence_id,
            "job_id": body.job_id,
            "user_id": job.get("user_id"),
            "worker_id": worker_id,
            "manifest": job.get("manifest"),
            "result_sha256": digest,
            "result_summary": result.get("summary") if isinstance(result, dict) else None,
            "scientific_status": "computational_hypothesis",
            "created_at": timestamp,
        }
        db.discovery_evidence_ledger.update_one({"_id": evidence_id}, {"$set": evidence}, upsert=True)
        db.discovery_screening_jobs.update_one(
            {"_id": body.job_id, "status": "running", "worker_id": worker_id},
            {
                "$set": {
                    "status": "completed",
                    "results": result,
                    "result_sha256": digest,
                    "evidence_id": evidence_id,
                    "completed_at": timestamp,
                    "updated_at": timestamp,
                },
                "$unset": {"lease_expires_at": ""},
            },
        )
        return {"ok": True, "job_id": body.job_id, "evidence_id": evidence_id, "result_sha256": digest}

    if body.action == "fail":
        if not body.job_id:
            raise HTTPException(status_code=422, detail="job_id is required")
        message = (body.error or "Worker failed without an error message").strip()[:4000]
        updated = db.discovery_screening_jobs.update_one(
            {"_id": body.job_id, "status": "running", "worker_id": worker_id},
            {
                "$set": {
                    "status": "failed",
                    "worker_error": message,
                    "failed_at": timestamp,
                    "updated_at": timestamp,
                },
                "$unset": {"lease_expires_at": ""},
            },
        )
        if updated.matched_count != 1:
            raise HTTPException(status_code=409, detail="Job is not leased to this worker")
        return {"ok": True, "job_id": body.job_id}

    if body.action == "status":
        return {
            "worker_id": worker_id,
            "queue": {
                "ready": db.discovery_screening_jobs.count_documents({"status": "ready_for_worker"}),
                "running": db.discovery_screening_jobs.count_documents({"status": "running"}),
                "completed": db.discovery_screening_jobs.count_documents({"status": "completed"}),
                "failed": db.discovery_screening_jobs.count_documents({"status": "failed"}),
            },
        }

    raise HTTPException(status_code=400, detail="Unsupported worker action")
