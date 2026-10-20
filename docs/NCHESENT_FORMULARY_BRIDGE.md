# NcheSent / FORMULARY synthetic research bridge

This repository contains NigerFlora BioSciences and its Research Studio; the independent `mabrig1/Formulary` GitHub repository does not currently exist. This PR links the existing Research Studio to `mabrig1/NcheSent` using the **synthetic-only phase-1 contract**, without merging platforms or their patient databases.

## Setup

1. Merge/deploy the companion NcheSent branch, and verify `GET https://nchesent.mabrigkorie.org/api/integrations/pharmaos/summary` (or `https://nchesent.pages.dev`).
2. Set `NCHESENT_BASE_URL=https://nchesent.mabrigkorie.org` or `https://nchesent.pages.dev` in the **NigerFlora Vercel** production and preview environment as appropriate. This must be a bare HTTPS origin. Don't enter an IP, API path, query string, or credential.
3. Deploy this branch. In NigerFlora, sign in → Research Studio → NcheSent Malaria Research Bridge. The frontend calls its own `/api/nchesent-bridge` route; Vercel routes that to `api/nchesent_bridge.py`. No CORS exception or browser-side upstream credentials required.
4. Test: `python -m unittest discover -s tests -p 'test_nchesent_bridge.py'`.

## Contract
Version `1.0`: only `source=NcheSent`, `dataset=synthetic`, `clinicalUse=false`, model version, generation time, synthetic assessment total, and separate counts by state / regimen / legacy \`byBand\` field containing \`NOT_SCORED\` only. Strict receiver validation refuses unexpected fields (e.g. patientId), inconsistent counts, non-synthetic data, oversized payloads, host redirects, and invalid sources. No records, patient identifiers, locations smaller than state, or clinical data. The receiver refuses requests until `NCHESENT_BASE_URL` is explicitly configured.

**Never interpret these demo counts as actual resistance, treatment failure or medication efficacy.** NcheSent v0.2 has retired provisional weighted risk scores. The receiver rejects any legacy LOW/MODERATE/HIGH classification; no model probabilities or treatment recommendations are exchanged. No prescriptive changes, personal data transfers, or clinical-data sync are authorized.

Future real-world interoperability must be a separate authenticated, authorized, versioned design with institution agreements, clinical governance, data-protection impact assessment, audit, encryption, de-identification/small-cell protection, validation, and clinical/regulatory approval.
