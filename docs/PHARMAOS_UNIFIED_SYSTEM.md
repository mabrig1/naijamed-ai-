# MABRIG PharmaOS — Unified Pharmaceutical Research System

This branch bundles the existing NigerFlora discovery stack and Formulary research/grant stack under one research lifecycle without replacing either engine.

## Lifecycle

Idea → evidence review → natural-product/compound intelligence → target/network pharmacology → docking/screening → ADMET → PK/PD → experimental planning → research portfolio → publication/regulatory work → grant studio → funder room.

## Existing capabilities retained

- NigerFlora research/discovery services
- Living Literature Review
- PK/PD Simulator
- Research Portfolio
- Regulatory & Grant Copilot
- Journal Club
- International Grant Project Studio
- Funder Due-Diligence Room
- RP-001 Nsukka UTI ethnobotany/antimicrobial pilot
- RP-002 NEXUS-AMR Africa

## New orchestration layer

`backend/app/pharmaos.py` provides a canonical module registry, ordered research pipeline and a grant handoff contract. It deliberately treats computational outputs as hypotheses/preliminary evidence until experimentally validated.

## Recommended next implementation slices

1. Wire authenticated `/api/pharmaos/modules` and `/api/pharmaos/projects/plan` endpoints.
2. Add a unified researcher command-centre UI that links existing routes instead of duplicating them.
3. Add an evidence ledger recording source IDs, software/model versions, parameters, timestamps and artifact hashes.
4. Add async compute adapters for docking/ML jobs; Kaggle is suitable for experimentation, not assumed as production SLA infrastructure.
5. Connect grant handoff to the existing Formulary Grant Project Studio.
6. Add supervisor/research-group dashboards only after RBAC and privacy review.

## Deployment boundary

This work is based on the Formulary PR branch, not the separate MediNaija Next.js migration. It does not merge, deploy, change Vercel settings, or expose private research artifacts.
