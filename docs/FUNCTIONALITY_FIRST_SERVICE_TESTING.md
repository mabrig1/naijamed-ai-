# NigerFlora Stage 1 — Seven Service Testing Checklist

## Purpose
All seven bioinformatics service cards must be testable without pricing, checkout, or an account. This is a research functionality test, not the delivery of full clinical or computational services.

| Service | Available for testing now | Still pending |
| --- | --- | --- |
| Bioinformatics Scope Consultation | Download local project-scoping and dataset-readiness brief | Actual expert consultation |
| ADMET & Drug-Likeness Screening | Live public PubChem compound reference search, method checklist | Validated RDKit and ADMET/toxicity modeling |
| Molecular Docking | Public ligand CID and RCSB PDB lookups, export setup-only Vina manifest | Docking simulation, scores and pose analysis |
| Network Pharmacology & Cytoscape | Verify source identifiers, export Cytoscape nodes CSV | Verified interactions, PPI and enrichment |
| Publication Figures | Export source-linked SVG test layout | Molecular 3D figures and publication-quality plotting |
| M.Sc./Ph.D. Research Package | Export integrated reproducibility plan and verified reference data | Computational study execution and validation |
| Department Analysis Bundle | Download departmental project plan | Multi-project operations and progress reporting |

## Test steps
1. Open /bioinformatics-services in a private browser window.
2. Confirm all seven cards show Test this workflow, without any prices or disabled-order buttons.
3. Open every card and download its research-brief file.
4. In the ADMET test, look up aspirin (PubChem CID 2244).
5. In the Docking test, look up aspirin and structure PDB 1CRN; download the setup-only manifest. The results field must be null.
6. In the Network test, export node metadata only. No invented interactions should appear.
7. In the Figures test, export an SVG source-reference layout; do not represent it as a calculated molecular structure.
8. Disconnect/mock the service catalog API: all test buttons must continue to work from the local catalog.
9. Verify new research order requests are rejected with HTTP 503 and no payment initialization occurs.
10. Verify all regular private operations, research saving, clinical records and owner management still require authentication.

## Operational boundaries
- Public research reference lookups are allowed without login. Saved research data and administrator actions are not.
- Research Studio hides service price labels and offers local research briefs.
- Server-side RESEARCH_CHECKOUT_ENABLED defaults to false for both research order APIs.
- Previously paid records and payment reconciliation remain intact; no new paid order can be created by the testing user interface.
- Public science records are not ADMET predictions, docking results, clinical recommendations or evidence of therapeutic efficacy.
- A successful GitHub test is not deployment verification. Confirm that Vercel publishes the exact revision before advertising the changes as live.
- The Vercel deployment rate limit reported earlier on November 14, 2026 must be cleared before publishing. Cloudflare is not an unreviewed fallback.

## Acceptance checks
Run the Python research checkout gate tests and the existing GitHub browser regression workflow. The browser test verifies all seven cards, price-free rendering, public lookup, and local downloads.
