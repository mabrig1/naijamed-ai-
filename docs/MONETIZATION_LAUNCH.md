# NigerFlora / NaijaMed AI — Monetization Launch

## Revenue architecture

The app now supports four complementary revenue lanes instead of relying on one product:

| Lane | Offer | Price / model |
|---|---|---|
| Consumer subscription | Family Health Pass | ₦5,000/month |
| Professional subscription | Doctor Workspace | ₦15,000/month |
| Research subscription | Formulary Scholar | ₦8,000/month |
| Marketplace | Verified doctor consultations | Provider-set fee; 18% platform commission |
| Research services | ADMET, docking, network pharmacology, research packages | Existing public package pricing |

Institutional clinic, HMO, campus and employer deals remain custom-quoted.

## What is implemented

- Public pricing page at `/pricing`.
- Paystack subscription checkout for Family Health Pass, Doctor Workspace and Formulary Scholar.
- Secure payment verification against the signed-in account.
- Subscription lifecycle persistence in MongoDB.
- Paystack webhook handling for:
  - initial successful charge;
  - subscription creation;
  - subscription disable / non-renewal;
  - failed recurring invoices;
  - successful recurring invoice updates.
- Account entitlement endpoint at `GET /api/clinical/subscriptions/me`.
- Existing provider-set consultation checkout and commission logic remains active.
- Existing bioinformatics storefront remains the high-ticket service lane.

## Paystack activation

Create three monthly plans in the same Paystack environment as `PAYSTACK_SECRET_KEY`:

1. **Family Health Pass**
   - interval: monthly
   - amount: ₦5,000 (500000 kobo)
   - save the returned `plan_code` as `FAMILY_PASS_PAYSTACK_PLAN_CODE`

2. **Doctor Workspace**
   - interval: monthly
   - amount: ₦15,000 (1500000 kobo)
   - save the returned `plan_code` as `DOCTOR_WORKSPACE_PAYSTACK_PLAN_CODE`

3. **Formulary Scholar**
   - interval: monthly
   - amount: ₦8,000 (800000 kobo)
   - save the returned `plan_code` as `FORMULARY_STUDENT_PAYSTACK_PLAN_CODE`

The app initializes the first transaction from the backend and passes the plan code. Paystack then creates the recurring subscription after the successful first payment.

Official Paystack references:
- https://paystack.com/docs/payments/subscriptions/
- https://paystack.com/docs/api/plan/
- https://paystack.com/docs/api/transaction/

## Required production variables

```dotenv
PAYSTACK_SECRET_KEY=
FAMILY_PASS_MONTHLY_KOBO=500000
FAMILY_PASS_PAYSTACK_PLAN_CODE=
DOCTOR_WORKSPACE_MONTHLY_KOBO=1500000
DOCTOR_WORKSPACE_PAYSTACK_PLAN_CODE=
FORMULARY_STUDENT_MONTHLY_KOBO=800000
FORMULARY_STUDENT_PAYSTACK_PLAN_CODE=
CONSULT_PLATFORM_FEE_PERCENT=18
FRONTEND_URL=https://nigerflora.mabrigkorie.org
```

## Webhook

Configure Paystack to send events to:

`https://nigerflora.mabrigkorie.org/api/clinical/webhooks/paystack`

The webhook signature is verified with HMAC-SHA512 before payment or subscription state changes are accepted.

## Positioning rules

- Essential AI-assisted intake and emergency red-flag escalation remain free.
- Subscriptions sell continuity, convenience and professional workflow—not guaranteed diagnosis, treatment results or emergency response.
- Doctor consultations are paid only after a verified provider and provider-set fee exist.
- Research services remain clearly separated from clinical claims.
- Institutional deals should be custom-quoted until support and usage economics are known.

## Launch checklist

1. Add live Paystack secret key in Vercel.
2. Create the three Paystack plans and add their plan codes.
3. Configure the clinical Paystack webhook.
4. Run one test checkout for each of the three subscriptions in Paystack test mode.
5. Verify `/pricing` displays all subscription plans and the signed-in account receives an active entitlement after payment.
6. Test one provider consultation payment and confirm the 18% platform fee is recorded.
7. Switch to live keys only after the test flows pass.
8. Track monthly recurring revenue, paid consultation GMV, platform commission, research-service revenue, checkout conversion and churn.


## Deployment topology check

The current Vercel Git integration reports `rootDirectory: frontend`.

That is sufficient to build the React/Vite application, but the Python serverless API in the repository-level `api/` directory is outside that Vercel project root. Before production rollout, confirm one of these architectures:

1. **Single Vercel project from repository root** — change the Vercel Root Directory from `frontend` to the repository root and use the root `vercel.json` build/output settings; or
2. **Separate frontend and backend deployments** — keep the frontend project rooted at `frontend`, deploy the Python API as its own project/service, and set `VITE_API_URL` to that backend origin.

Do not treat a green frontend Vercel build as proof that the Python endpoints are live. Health-check the following routes against the production API before enabling paid traffic:

- `GET /api/clinical/plans`
- `GET /api/formulary` (authenticated)
- `GET /api/formulary/pkpd/runs` (authenticated)
- `GET /api/formulary/portfolio` (authenticated)
- `GET /api/formulary/portfolio/public/{slug}`
- `POST /api/clinical/subscriptions/checkout`
- `POST /api/formulary/pkpd/nca`

