"""Synthetic-only NcheSent research summary bridge for NigerFlora / PharmaOS.

This intentionally NEVER accepts patient-level records or real surveillance feeds.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

app = FastAPI(title="NigerFlora ↔ NcheSent Research Bridge", version="1.0.0")

# Fixed destination allowlist prevents the server endpoint being an open HTTP proxy.
TRUSTED_HOSTS = {"nchesent.mabrigkorie.org", "nchesent.pages.dev"}


class NcheSentSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schemaVersion: Literal["1.0"]
    source: Literal["NcheSent"]
    dataset: Literal["synthetic"]
    clinicalUse: Literal[False]
    modelVersion: str = Field(min_length=1, max_length=40)
    generatedAt: str = Field(min_length=10, max_length=35)
    totalAssessments: int = Field(ge=0, le=10000)
    byState: dict[str, int]
    byRegimen: dict[str, int]
    byBand: dict[str, int]
    notice: str = Field(min_length=10, max_length=500)

    @model_validator(mode="after")
    def validate_safe_aggregates(self):
        try:
            datetime.fromisoformat(self.generatedAt.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("generatedAt must be ISO-8601") from exc

        for field in ("byState", "byRegimen", "byBand"):
            counts = getattr(self, field)
            if len(counts) > 50 or any(
                not isinstance(k, str) or not k or len(k) > 60 or
                type(v) is not int or v < 0 or v > 10000
                for k, v in counts.items()
            ) or sum(counts.values()) != self.totalAssessments:
                raise ValueError(f"Invalid {field} aggregate")
        # NcheSent v0.2 no longer emits provisional clinical score bands.
        # Fail closed on old LOW/MODERATE/HIGH counts instead of re-labelling
        # unvalidated values as malaria-risk surveillance.
        if self.byBand != {"NOT_SCORED": self.totalAssessments}:
            raise ValueError("Only NOT_SCORED synthetic assessments are accepted")
        return self


def configured_upstream() -> str:
    raw = os.environ.get("NCHESENT_BASE_URL", "").strip()
    if not raw:
        raise HTTPException(status_code=503, detail="NcheSent research bridge not configured")
    url = urlsplit(raw)
    if (
        url.scheme != "https"
        or url.hostname not in TRUSTED_HOSTS
        or url.port not in (None, 443)
        or url.username is not None
        or url.password is not None
        or url.path not in ("", "/")
        or url.query or url.fragment
    ):
        raise HTTPException(status_code=503, detail="NcheSent bridge host configuration is invalid")
    return f"https://{url.hostname}"


@app.get("/api/nchesent_bridge", response_model=NcheSentSummary)
async def nchesent_summary() -> NcheSentSummary:
    target = configured_upstream() + "/api/integrations/pharmaos/summary"
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=False, trust_env=False) as client:
            response = await client.get(target, headers={"Accept": "application/json"})
        if response.status_code != 200 or len(response.content) > 16384:
            raise HTTPException(status_code=502, detail="NcheSent summary unavailable")
        return NcheSentSummary.model_validate_json(response.content)
    except (httpx.HTTPError, ValidationError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="NcheSent summary unavailable or failed research-only validation") from exc
