# PharmaOS Remote Research Computation (NcheSent)

The separate NigerFlora BioSciences / MABRIG PharmaOS application contains a **Python descriptive computation engine** for NcheSent's fabricated malaria follow-up data.

- API: `POST /api/nchesent-analysis` (Vercel rewrite into `api/nchesent_analysis.py`).
- Caller: NcheSent Cloudflare Worker endpoint `GET /api/integrations/pharmaos/analysis`.
- Input: exactly 9 aggregate day buckets (days 0/1/2/3/7/14/21/28/42), synthetic counts and density sums only, with `dataset=synthetic`, `clinicalUse=false`, `scored=false`, `modelVersion=0.2.0`.
- Output: daily documentation coverage, number tested, fabricated positive fraction (per tested), arithmetic mean of recorded synthetic parasite density, and overall fictional visit-slot completeness.
- Storage: **none**. No real data, no patient-level records, no LLM, GPU, PCR correction, parasite-clearance kinetic model, case classification, treatment advice, or resistance prediction.
- Input validation: Pydantic `extra=forbid`, strict type checks, fixed day sequence, count identities and cohort denominator consistency. Invalid input returns HTTP 422.

Run computation contract tests:

```bash
python -m unittest discover -s tests -p "test_nchesent_analysis.py"
```

The NcheSent client uses a server-to-server POST to this Vercel service; no browser CORS and no NCHESENT_BASE_URL variable is needed for this **forward computation flow**. The existing reverse Research Studio GET summary bridge remains separate and will continue to display unavailable until NCHESENT_BASE_URL is configured to a verified NcheSent deployment.

**Warning:** Fictional test positivity is not WHO treatment failure, efficacy, clearance, an adverse outcome, or patient-level time-to-event analysis. These aggregate day buckets do not preserve individual trajectories and cannot establish clinical response. Before building a real study module, follow approved clinical protocols, WHO therapeutic-efficacy study data standards, ethics, consent, privacy and clinical validation.

WHO methods: https://www.who.int/teams/global-malaria-programme/case-management/drug-efficacy-and-resistance/tools-for-monitoring-antimalarial-drug-efficacy
