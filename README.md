# NigerFlora BioSciences

NigerFlora BioSciences is an agentic healthcare, ethnobotanical research and computational discovery platform for Nigeria. Its production architecture is intentionally simple: **React/Vite + FastAPI on Vercel, MongoDB Atlas for application data, and Qdrant for medically reviewed retrieval-augmented clinical knowledge**.

## Production URLs

- Canonical public domain: `https://nigerflora.mabrigkorie.org`
- Vercel deployment alias: `https://nigerflora-biosciences.vercel.app`

The custom domain is the preferred URL for users, payment callbacks and public links. The Vercel alias remains an allowed origin and operational fallback.

## Production architecture

```text
Patient / Researcher / Doctor / Clinic
               |
               v
       React + Vite frontend
               |
               v
   Vercel Python FastAPI (/api/*)
               |
       +-------+--------------------+
       |                            |
       v                            v
 MongoDB Atlas                Agent workflows
 users/cases/orders           clinical + research studio
                                    |
                         +----------+----------+
                         v                     v
                    Qdrant RAG          External services
                                    Paystack / maps / voice
```

### Core stack

| Layer | Production technology |
|---|---|
| Hosting / CI | Vercel Git deployments + preview deployments |
| Frontend | React, Vite, TypeScript, Tailwind CSS |
| API | FastAPI on the Vercel Python runtime |
| Primary database | MongoDB Atlas |
| Clinical orchestration | LangGraph |
| Clinical RAG | Qdrant + reviewed Nigerian/WHO protocol chunks |
| Payments | Paystack |
| Voice | OpenAI transcription API |
| Low-bandwidth | Africa's Talking SMS / USSD |
| Maps | OpenStreetMap/Nominatim + internal verified-provider registry |

## Monetization

Public pricing: `/pricing`

Recurring clinical revenue is built around a **Family Health Pass (₦5,000/month)** and **Doctor Workspace (₦15,000/month)** using Paystack subscriptions. Verified doctor consultations use provider-set fees with a configurable platform commission, while the existing bioinformatics storefront remains the high-ticket research-services lane.

Production subscription variables:

```dotenv
FAMILY_PASS_MONTHLY_KOBO=500000
FAMILY_PASS_PAYSTACK_PLAN_CODE=PLN_...
DOCTOR_WORKSPACE_MONTHLY_KOBO=1500000
DOCTOR_WORKSPACE_PAYSTACK_PLAN_CODE=PLN_...
CONSULT_PLATFORM_FEE_PERCENT=18
```

See `docs/MONETIZATION_LAUNCH.md` for the complete activation and test checklist.

## Formulary

Formulary is the postgraduate pharmaceutical research workspace inside NigerFlora. Its first production MVP is a **Living Literature Review** that converts DOI metadata and authorized PDF uploads into structured pharmaceutical evidence tables, preserves researcher corrections with provenance, and refreshes incoming citations through OpenAlex.

Route: `/formulary`

Default commercial tier: **Formulary Scholar — ₦8,000/month**, configurable through environment variables.

See `docs/FORMULARY_MVP.md` for architecture, research-integrity rules and rollout metrics.


### Implemented Formulary modules

- **Living Literature Review** — DOI/PDF evidence extraction, corrections and citation watch.
- **PK/PD Simulator** — NCA and one-compartment educational/research simulations.
- **Rotation & Research Portfolio** — PharmD/residency/postgraduate milestones with optional attestations.
- **Regulatory & Grant Copilot** — source-grounded FDA/ICH/NIH drafting with traceable source snapshots.
- **Journal Club Live Room** — collaborative critical appraisal, linked evidence, action items and evidence-grounded fact checks.
- **International Grant Project Studio** — consortium planning, work-package budgets, milestones, background-IP register, controlled-disclosure ledger and grant-readiness checks.

Routes: `/formulary`, `/formulary/pkpd`, `/formulary/portfolio`, `/formulary/copilot`, `/formulary/journal`, `/formulary/grants`.


## Research & Discovery Studio

NigerFlora includes a monetizable research-services layer for:

- network pharmacology consulting;
- ADMET and drug-likeness screening;
- molecular docking support;
- in-silico thesis packages;
- publication-ready scientific figures;
- herbal research grant/proposal architecture;
- practical in-silico research training;
- experimental Polyherbal Synergy Index (PSI-β) projects.

Computational outputs are hypothesis-generating research evidence. They are not automatic proof of therapeutic efficacy, safety, patentability or regulatory approval.

## Vercel deployment

Vercel detects `api/index.py` as the FastAPI entrypoint. Requests under `/api/*` are handled by Python functions, while the React build is served from `frontend/dist`. The frontend API client automatically uses the current browser origin in production, so both production domains can call their own `/api/*` routes without a hard-coded localhost address.

### Required production environment variables

```dotenv
APP_NAME="NigerFlora BioSciences"
MONGODB_URI=mongodb+srv://...
MONGODB_DB=mabrig_healthos
SECRET_KEY=<long-random-secret>
PHI_ENCRYPTION_KEY=<32-byte-base64url-or-hex-key>
GEMINI_API_KEY=<key>
PAYSTACK_SECRET_KEY=<key>
FRONTEND_URL=https://nigerflora.mabrigkorie.org
EXTRA_CORS_ORIGINS=https://nigerflora-biosciences.vercel.app
```

Recommended integrations:

```dotenv
QDRANT_URL=
QDRANT_API_KEY=
OPENAI_API_KEY=
AFRICASTALKING_USERNAME=
AFRICASTALKING_API_KEY=
ADMIN_EMAILS=admin@example.com
```

## MongoDB Atlas collections

The application creates indexes automatically on first successful connection. Primary collections include:

- `users`
- `clinical_cases`
- `provider_profiles`
- `clinical_consultations`
- `clinical_audit_logs`
- `research_service_orders`
- `polyherbal_synergy_projects`

Clinical case payloads are encrypted before storage using AES-256-GCM. Keep `PHI_ENCRYPTION_KEY` only in Vercel environment variables; never commit it.

## Local development

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
npm --prefix frontend install
vercel dev
```

Then open the local URL shown by Vercel. Production should use `https://nigerflora.mabrigkorie.org`.

## Clinical safety boundary

NigerFlora BioSciences is clinical decision support, not an autonomous doctor. Deterministic red-flag rules run before the LLM. The system does not autonomously prescribe medication or provide medication doses. Differential considerations are generated only when reviewed evidence is retrieved, and treatment decisions remain with licensed clinicians.

Before public clinical launch, complete independent medical advisory review, provider-licence verification procedures, privacy/data-protection assessment, incident response, penetration testing, and validation of the clinical knowledge corpus.

## Legacy source

Older herbal-marketplace SQLAlchemy modules remain for source/history compatibility, but they are **not imported by the Vercel production entrypoint and do not require a PostgreSQL service for deployment**.
