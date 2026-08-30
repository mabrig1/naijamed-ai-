# NigerFlora BioSciences — Bioinformatics Revenue Launch

This document turns the Research & Discovery Studio into an immediately sellable consulting operation for Nigeria and international clients.

## Public storefront

Primary sales page:

- `/bioinformatics-services`

Primary offers:

1. Bioinformatics Scope Consultation — ₦25,000 / $39
2. ADMET & Drug-Likeness Screening — from ₦75,000 / $110
3. Network Pharmacology & Cytoscape Analysis — from ₦120,000 / $180
4. Molecular Docking Simulation Service — from ₦150,000 / $220
5. Publication-Ready Scientific Figure Pack — from ₦60,000 / $90
6. M.Sc./Ph.D. Computational Research Package — from ₦300,000 / $450
7. Academic Department Analysis Bundle — ₦650,000 / $950

These are NigerFlora starting prices, not claims about market-average pricing. Oversized datasets or unusually complex workflows should be custom quoted before work begins.

## Payment activation

Add these in Vercel Production Environment Variables:

- `PAYSTACK_SECRET_KEY`
- `FLUTTERWAVE_SECRET_KEY` (optional but recommended for global checkout)

Paystack is the default Nigeria/NGN checkout. International Paystack card/USD acceptance depends on the merchant account being approved/enabled for international payments and the requested settlement currency.

Flutterwave is the recommended secondary international checkout path. The hosted checkout avoids handling card details directly inside NigerFlora.

Configure the Paystack webhook URL as:

`https://nigerflora.mabrigkorie.org/api/research-commerce/paystack-webhook`

The webhook is signature-verified and can activate an order even when a customer closes the browser before returning to the site.

## First offers to promote

### Local — UNN / Nsukka / Nigerian postgraduate market

Lead with:

- ₦25,000 scope consultation for uncertain projects
- ₦75,000 ADMET package for quick-turn compound screens
- ₦120,000 network pharmacology/Cytoscape package
- ₦150,000 docking starter package
- ₦300,000 integrated M.Sc./Ph.D. computational package

Position the service around reproducibility, defendable methods, clear deliverables and figure quality rather than promises of guaranteed publication or guaranteed biological activity.

Suggested local outreach targets:

- postgraduate students in biological sciences, pharmacy, biochemistry, pharmacology, microbiology and related disciplines
- supervisors handling multiple computational projects
- faculty/department postgraduate WhatsApp groups where promotion is permitted
- research labs and academic departments
- herbal/drug discovery research teams

### International

Lead with:

- $39 scope consultation
- $110 ADMET screening
- $180 network pharmacology starter
- $220 molecular docking starter
- $450 integrated postgraduate computational package
- $950 department/lab bundle

Suggested acquisition channels:

- LinkedIn research communities and direct professional outreach
- ResearchGate profile/project visibility where platform rules permit
- academic and computational biology communities
- freelance/research-services marketplaces where the service complies with marketplace and academic-integrity rules
- diaspora researchers and African research networks

## Fulfillment standard

Every paid order should move through these statuses:

1. `intake` — confirm question, compounds/targets, dataset and expected output
2. `queued` — scope accepted and scheduled
3. `running` — analysis in progress
4. `review` — internal QC and client preview
5. `delivered` — final files supplied
6. `revision` — agreed correction/revision cycle, if needed
7. `closed` — completed and archived

Admin route:

- `/research-commerce/admin`

The admin dashboard shows paid revenue, active projects, sales leads and order status. It supports progress percentages, target delivery dates, client-facing notes and secure deliverable links.

## Scientific deliverable standards

### Molecular docking

Minimum package evidence:

- target/receptor identity and source
- ligand identifiers and structures
- preparation workflow
- docking box coordinates/size
- engine/version where known
- exhaustiveness, number of modes and seed where applicable
- ranked docking output
- interaction/residue summary
- high-resolution structural figures
- reproducibility manifest

Do not invent docking scores. Heavy AutoDock Vina/GROMACS compute remains an external-worker or researcher-operated workflow; the Vercel app stores project state, identifiers, manifests and deliverables.

### Network pharmacology / Cytoscape

Minimum package evidence:

- compound and target source table
- identifier-normalization record
- target/disease mapping source notes
- network node/edge tables
- Cytoscape-ready network files
- stated network metrics
- high-resolution network figures
- transparent limitations

### ADMET

Minimum package evidence:

- compound identifiers/SMILES audit
- source/tool/model details
- exportable ADMET matrix
- explicit inclusion/exclusion criteria
- prioritization table
- limitations explaining that predictions are not clinical or regulatory proof

### Publication-ready figures

Default delivery target:

- 300–600 DPI PNG/TIFF where appropriate
- journal-size variants
- editable source/session file where the source tool supports it
- figure legend
- reproducibility label/source note

## Fast conversion principles

- Keep a low-friction paid consultation as the entry product.
- Show exact package boundaries and prices publicly.
- Make payment possible immediately after registration.
- Publish progress after payment so clients are not forced to ask for updates.
- Deliver through access-controlled links rather than public files.
- Ask for testimonials only after successful delivery and with client consent.
- Never advertise guaranteed publication, guaranteed docking outcomes, guaranteed therapeutic efficacy or guaranteed regulatory approval.

## Operational checks before promotion

- Vercel production deployment is green.
- MongoDB production connection is working.
- At least one admin account has role `admin`.
- Paystack secret key is configured and a small live/test order has been verified.
- Paystack webhook is configured and signature verification succeeds.
- If using Flutterwave, the secret key is configured and one hosted-checkout return has been verified.
- Delivery storage/link workflow is ready (for example access-controlled Drive or R2 links).
- A sample deliverable pack exists for each high-demand service so prospective clients can understand quality without exposing another client's confidential work.
