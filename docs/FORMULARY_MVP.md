# Formulary — Living Literature Review MVP

**Tagline:** The operating system for translational pharmaceutical science.

Formulary is a postgraduate pharmaceutical research workspace inside NigerFlora/NaijaMed AI. The first MVP focuses on the highest-frequency pain point: converting scattered papers into a structured, living evidence table.

## MVP workflow

1. Create a living review with a research question and optional inclusion/exclusion criteria.
2. Add a paper by DOI or upload a PDF the user is authorized to use.
3. Formulary extracts and structures:
   - study design;
   - population;
   - sample size;
   - intervention and comparator;
   - dosing regimen;
   - primary endpoints;
   - p-values and confidence intervals;
   - adverse events;
   - PK parameters: AUC, Cmax, Tmax, half-life, clearance, volume of distribution and bioavailability.
4. The researcher corrects any field that is wrong.
5. Every correction is preserved with the prior value, new value, author, timestamp and optional verification note.
6. Citation Watch queries OpenAlex for newer works citing an included paper.
7. The review can be exported as CSV for Excel, SPSS, R or downstream analysis.

## External metadata

### Crossref

Crossref supplies DOI bibliographic metadata and, where deposited, abstracts.

Production settings:

```dotenv
CROSSREF_MAILTO=research@example.org
```

A mailto value is optional but recommended for polite-pool usage.

### OpenAlex

OpenAlex supplies DOI matching, citation counts and incoming-citation discovery.

```dotenv
OPENALEX_API_KEY=
```

The MVP works without a key for low-volume use. Add a free OpenAlex key before wider rollout so usage can be tracked and the daily allowance is higher.

## Formulary Scholar

Default product configuration:

```dotenv
FORMULARY_STUDENT_MONTHLY_KOBO=800000
FORMULARY_STUDENT_PAYSTACK_PLAN_CODE=
FORMULARY_FREE_REVIEW_LIMIT=2
FORMULARY_FREE_PAPER_LIMIT=10
FORMULARY_PDF_MAX_BYTES=12582912
FORMULARY_LLM_MODEL=
```

### Free researcher

- 2 living reviews
- 10 evidence papers total
- DOI import
- PDF extraction
- evidence correction provenance

### Formulary Scholar

- unlimited living reviews;
- unlimited evidence entries;
- structured PDF extraction;
- citation-watch workflow;
- future advanced modules as they launch.

The listed price is currently ₦8,000/month but is environment-configurable.

## Data-moat design

The moat is **structured researcher-verified evidence**, not silent harvesting.

Each extraction can be corrected by the researcher, and the review records whether the user consented to de-identified corrections being considered for future model improvement. Consent is off by default. The current MVP stores corrections for provenance and does not automatically send them into a training pipeline.

## Research integrity and copyright boundary

- PDF extraction is only for documents the user is authorized to upload and analyze.
- The app does not automatically scrape publisher paywalls.
- DOI ingestion uses metadata and abstracts exposed by scholarly metadata services.
- Extracted values must be checked against the source before publication, clinical use, regulatory submission or grant submission.
- Formulary must not fabricate missing values.

## PK/PD Simulator — implemented

Route: `/formulary/pkpd`

The first simulator release includes:

- observed-data noncompartmental analysis using linear trapezoidal AUC;
- observed Cmax and Tmax;
- terminal log-linear regression using a user-selected 3–8 terminal points;
- λz, terminal half-life and terminal-fit R²;
- AUC₀–last, AUC extrapolation and AUC₀–∞;
- warnings when terminal fit is weak or >20% of AUC∞ is extrapolated;
- IV clearance and Vz when an IV dose is explicitly supplied;
- one-compartment IV-bolus simulation;
- one-compartment oral simulation with first-order absorption and user-supplied bioavailability;
- concentration–time visualization and persistent saved runs.

Free accounts receive 3 saved PK/PD runs. Formulary Scholar receives unlimited simulator access.

The simulator is for research and teaching. It does not select or recommend patient doses.

## Roadmap

### Phase 3 — Residency / Research Portfolio

Clinical interventions, rotation milestones, lab presentations, committee meetings, grant deadlines and verified output portfolio.

### Phase 4 — Regulatory & Grant Copilot

Evidence-grounded drafting against FDA, ICH and user-controlled literature libraries with exact-source citations.

### Phase 5 — Journal Club Live Room

Shared paper room, structured extraction table, discussion notes and evidence checking during journal club.

## Launch target

Initial pilot:

- 50 postgraduate pharmaceutical researchers/programs;
- measure papers imported per active user;
- extraction correction rate;
- weekly citation refreshes;
- time saved per review;
- free-to-Scholar conversion;
- repeat review creation;
- team/institution invite demand.

The key KPI is not raw uploads. It is **researchers returning to the same structured evidence workspace every week**.
