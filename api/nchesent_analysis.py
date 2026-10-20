"""NcheSent -> NigerFlora PharmaOS: strictly synthetic descriptive computation.

No patient records, clinical predictions, treatment guidance, persistence or
inferred resistance. Receives nine aggregate day buckets from fictional fixtures.
"""
from __future__ import annotations

import math
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field, model_validator

app = FastAPI(title="MABRIG PharmaOS Synthetic Malaria Research Compute", version="1.0.0")
VISIT_DAYS = (0, 1, 2, 3, 7, 14, 21, 28, 42)
NOTICE = (
    "Fictional aggregate arithmetic only. This is NOT a clinical prediction, "
    "patient parasite-clearance curve, WHO therapeutic efficacy endpoint, "
    "drug resistance estimate or antimalarial treatment recommendation."
)


class DayCounts(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    day: Literal[0, 1, 2, 3, 7, 14, 21, 28, 42]
    documented: int = Field(ge=0, le=10000)
    tested: int = Field(ge=0, le=10000)
    positive: int = Field(ge=0, le=10000)
    negative: int = Field(ge=0, le=10000)
    notTested: int = Field(ge=0, le=10000)
    missing: int = Field(ge=0, le=10000)
    densityCount: int = Field(ge=0, le=10000)
    densitySum: int = Field(ge=0, le=10_000_000_000)

    @model_validator(mode="after")
    def check_day(self):
        if self.tested != self.positive + self.negative:
            raise ValueError("tested count must equal positive plus negative")
        if self.documented != self.tested + self.notTested:
            raise ValueError("documented count must equal tested plus not-tested")
        if self.densityCount > self.tested:
            raise ValueError("density observations cannot exceed tested results")
        if self.densityCount == 0 and self.densitySum != 0:
            raise ValueError("densitySum must be zero when densityCount is zero")
        return self


class SyntheticCohort(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schemaVersion: Literal["1.0"]
    source: Literal["NcheSent"]
    dataset: Literal["synthetic"]
    clinicalUse: Literal[False]
    scored: Literal[False]
    analysisType: Literal["synthetic_longitudinal_counts"]
    modelVersion: Literal["0.2.0"]
    totalExamples: int = Field(ge=1, le=10000)
    days: list[DayCounts] = Field(min_length=9, max_length=9)

    @model_validator(mode="after")
    def check_cohort(self):
        if tuple(row.day for row in self.days) != VISIT_DAYS:
            raise ValueError("Exactly one ordered bucket for each scheduled demo day required")
        for row in self.days:
            if row.documented + row.missing != self.totalExamples:
                raise ValueError("documented and missing must sum to cohort total")
        return self


def analyze_synthetic_cohort(cohort: SyntheticCohort) -> dict:
    """Deterministic, descriptive aggregate math; explicitly NO patient modelling."""
    daily = []
    total_slots = cohort.totalExamples * len(cohort.days)
    documented_sum = 0
    positive_sum = 0
    tested_sum = 0

    for row in cohort.days:
        documented_sum += row.documented
        positive_sum += row.positive
        tested_sum += row.tested

        daily.append({
            "day": row.day,
            "documented": row.documented,
            "tested": row.tested,
            "positive": row.positive,
            "negative": row.negative,
            "notTested": row.notTested,
            "missing": row.missing,
            "documentationPercent": round(100.0 * row.documented / cohort.totalExamples, 1),
            # A percentage of fictional tests: not a patient outcome or efficacy estimate.
            "syntheticPositivityPercent": (
                round(100.0 * row.positive / row.tested, 1) if row.tested else None
            ),
            "meanRecordedDensity": (
                round(row.densitySum / row.densityCount, 1) if row.densityCount else None
            ),
        })

    return {
        "schemaVersion": "1.0",
        "source": "NigerFlora PharmaOS",
        "inputSource": "NcheSent",
        "engine": "deterministic-descriptive-v1",
        "dataset": "synthetic",
        "clinicalUse": False,
        "scored": False,
        "totalExamples": cohort.totalExamples,
        "summary": {
            "visitSlots": total_slots,
            "documentedVisitSlots": documented_sum,
            "missingVisitSlots": total_slots - documented_sum,
            "documentationPercent": round(100.0 * documented_sum / total_slots, 1),
            "testedObservations": tested_sum,
            "positiveObservations": positive_sum,
        },
        "days": daily,
        "limitations": [
            "Daily buckets are unlinked aggregate counts; no individual clearance curve or time-to-event outcome can be calculated.",
            "No PCR correction, adverse events, withdrawals, loss-to-follow-up analysis or protocol-specific WHO outcome classification.",
            "Synthetic percentages and density averages must never be presented as real malaria efficacy or resistance evidence.",
        ],
        "notice": NOTICE,
    }


@app.post("/api/nchesent_analysis")
async def nchesent_analysis(cohort: SyntheticCohort) -> dict:
    return analyze_synthetic_cohort(cohort)
