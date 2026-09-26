# NigerFlora / NaijaMed AI — Monetization Launch

## Revenue architecture

The app now supports four complementary revenue lanes instead of relying on one product:

| Lane | Offer | Price / model |
|---|---|---|
| Consumer subscription | Family Health Pass | ₦5,000/month |
| Professional subscription | Doctor Workspace | ₦15,000/month |
| Marketplace | Verified doctor consultations | Provider-set fee; 18% platform commission |
| Research services | ADMET, docking, network pharmacology, research packages | Existing public package pricing |

Institutional clinic, HMO, campus and employer deals remain custom-quoted.

## What is implemented

- Public pricing page at `/pricing`.
- Paystack subscription checkout for Family Health Pass and Doctor Workspace.
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

Create two monthly plans in the same Paystack environment as `PAYSTACK_SECRET_KEY`:

1. **Family Health Pass**
   - interval: monthly
   - amount: ₦5,000 (500000 kobo)
   - save the returned `plan_code` as `FAMILY_PASS_PAYSTACK_PLAN_CODE`

2. **Doctor Workspace**
   - interval: monthly
   - amount: ₦15,000 (1500000 kobo)
   - save the returned `plan_code` as `DOCTOR_WORKSPACE_PAYSTACK_PLAN_CODE`

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
2. Create the two Paystack plans and add their plan codes.
3. Configure the clinical Paystack webhook.
4. Run one test checkout for each subscription in Paystack test mode.
5. Verify `/pricing` displays both plans and the signed-in account receives an active entitlement after payment.
6. Test one provider consultation payment and confirm the 18% platform fee is recorded.
7. Switch to live keys only after the test flows pass.
8. Track monthly recurring revenue, paid consultation GMV, platform commission, research-service revenue, checkout conversion and churn.
