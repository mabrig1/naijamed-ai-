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
FORMULARY_FREE_PK_RUN_LIMIT=3
FORMULARY_FREE_PORTFOLIO_ITEM_LIMIT=25
FORMULARY_FREE_COPILOT_WORKSPACE_LIMIT=1
FORMULARY_FREE_COPILOT_DRAFT_LIMIT=3
FORMULARY_FREE_JOURNAL_ROOM_LIMIT=2
FORMULARY_FREE_JOURNAL_FACTCHECK_LIMIT=10
FORMULARY_FREE_GRANT_PROJECT_LIMIT=1
FORMULARY_PDF_MAX_BYTES=12582912
FORMULARY_LLM_MODEL=
```

### Free researcher

- 2 living reviews
- 10 evidence papers total
- DOI import
- PDF extraction
- evidence correction provenance
- 3 saved PK/PD runs
- 25 residency/research portfolio items
- 1 regulatory/grant copilot workspace
- 3 generated copilot drafts
- 2 Journal Club rooms
- 10 evidence-grounded Journal Club fact checks

### Formulary Scholar

- unlimited living reviews;
- unlimited evidence entries;
- structured PDF extraction;
- citation-watch workflow;
- unlimited PK/PD simulator runs;
- unlimited residency/research portfolio tracking;
- opt-in public portfolio and supervisor/preceptor attestations;
- unlimited regulatory/grant copilot workspaces and drafts;
- unlimited Journal Club rooms and fact checks;
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

## Rotation & Research Portfolio — implemented

Route: `/formulary/portfolio`

The tracker supports PharmD, residency, M.Sc., Ph.D. and custom postgraduate tracks. It includes:

- configurable program profile, specialty, dates and competency framework;
- rotations / learning experiences;
- clinical interventions;
- development-plan entries and evaluations;
- research and laboratory milestones;
- thesis / committee milestones;
- presentations and journal clubs;
- publications, grants and fellowships;
- teaching, certification and coursework records;
- hours, outcomes/reflections and evidence URLs;
- private/public visibility per portfolio item;
- opt-in public portfolio page;
- 14-day private supervisor/preceptor attestation links tied to the intended verifier email.

Attestation is deliberately described as **attestation**, not independent credential verification. Formulary records the verifier response, name, role and organization but does not independently certify employment, licensure or institutional identity.

The architecture is intentionally configurable rather than claiming automatic ASHP compliance. Current ASHP residency resources emphasize learning experiences, schedules, evaluations, resident development plans, objectives and portfolio/file management; institutions can map those workflows into their own Formulary competency framework.

References:
- https://www.ashp.org/professional-development/residency-information/residency-program-resources/pharmacademic
- https://www.ashp.org/professional-development/residency-information/residency-program-resources

## Regulatory & Grant Copilot — implemented

Route: `/formulary/copilot`

The copilot is source-grounded by design. A workspace can combine:

- curated official FDA, ICH and NIH source metadata;
- selected Formulary Living Reviews and their structured paper evidence;
- user-supplied NOFO, guidance or institutional excerpts;
- researcher notes and jurisdiction constraints.

Implemented draft types:

- NIH Specific Aims;
- NIH Research Strategy;
- grant application planning;
- regulatory strategy briefs;
- CTD / eCTD dossier plans;
- protocol outlines;
- compliance-gap analyses.

Every generated draft stores:

- the exact source snapshot used;
- inline `[SRC:source-id]` references;
- generation method;
- deterministic gap checks;
- selected literature review IDs;
- unresolved verification items.

The engine rejects invented source IDs. If the configured AI service is unavailable, it returns a deterministic structured working template rather than fabricating unsupported prose.

Current curated source registry includes ICH E6(R3), ICH M4 CTD, ICH eCTD v4.0, FDA clinical-pharmacology guidance and current NIH application/page-limit guidance. Draft guidance is explicitly labeled as draft.

The researcher remains responsible for checking the current regulator, regional implementation documents, exact NOFO, institutional research office, ethics requirements and source text before submission.

## Journal Club Live Room — implemented

Route: `/formulary/journal`

Journal Club rooms connect structured literature evidence with collaborative appraisal. Implemented features include:

- room scheduling and scheduled/live/closed lifecycle;
- optional external Zoom / Google Meet / Teams link;
- private hashed invite tokens for authenticated participants;
- invite rotation, room locking and host controls;
- linked Formulary Living Review papers;
- structured evidence table without exposing uploaded PDF bytes or private source excerpts;
- general, randomized-trial and PK-study critical-appraisal templates;
- collaborative notes, questions, claims, decisions and action items;
- competency-independent discussion records with author and timestamps;
- evidence-grounded claim fact checks restricted to papers linked to the room;
- explicit supported / contradicted / mixed / unclear verdicts with confidence and `PAPER:entry-id` citations;
- conservative deterministic fallback when the AI model is unavailable;
- periodic refresh while a room is marked Live;
- exportable Markdown meeting record;
- protected deep-link return flow so invitees can sign in or create an account without losing the room invitation.

The room shares structured article metadata/extractions, not the owner's uploaded PDF file or stored source excerpt. Important claims must still be verified against the original article.

## Roadmap

Future high-value additions can include native WebRTC/video, institutional cohorts, CE accreditation workflows, calendar invitations and organization analytics.

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


## International Grant Project Studio — implemented

Route: `/formulary/grants`

The Grant Project Studio moves large international research projects beyond a single draft into a managed programme workspace.

Implemented capabilities:

- flagship, consortium, implementation, fellowship and infrastructure project types;
- project originator, proposed host, country/location, duration and total budget;
- funder, call reference, official call URL and deadline tracking;
- executive summary, problem statement and specific objectives;
- concept → institutional engagement → consortium building → drafting → review → submission lifecycle;
- consortium partner map with country, type, contact, proposed role and commitment status;
- work-package architecture with sequence, lead, objectives, outputs and budget;
- automatic work-package budget reconciliation against total project budget;
- critical-path milestones with owner, due date and status;
- Background IP / pre-existing asset register;
- controlled-disclosure ledger recording recipient, organisation, date, material/version, purpose and confidentiality basis;
- generated controlled-disclosure watermark;
- deterministic grant-readiness assessment with explicit gaps and risk flags;
- NEXUS-AMR Africa starter template for the current UNN/Nsukka flagship concept.

The readiness engine checks proposal substance, named funding target, deadline, work-package structure, budget reconciliation, consortium depth, international partner participation, partner commitment, milestones, background-IP evidence and disclosure controls.

Important boundary: the Studio creates a dated operational/evidentiary trail. It does not by itself create patent rights, guarantee legal ownership or replace a signed NDA/MOU/IP agreement, funder rules, institutional policy or qualified legal review.
