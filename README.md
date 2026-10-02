# MediNaija

**Your chronic care companion — drugs, delivery, and check-ins in one plan.**

MediNaija is the chronic-care MVP now wired into this repository. The root application is Next.js 14 + TypeScript + Tailwind/shadcn-style components, backed by Supabase. The previous NigerFlora React/Vite + FastAPI source is intentionally preserved under the existing `frontend/`, `backend/` and root `api/` folders for reference while the MediNaija migration is validated.

## Current implementation

### Phase 1
- Phone + SMS OTP authentication through Supabase Auth
- Explicit health-data consent screen
- Three-step onboarding for conditions, current medicine source and monthly budget
- Profile with name, DOB, state, LGA, email and next-of-kin
- Dashboard showing next refill, adherence streak and monthly successful-payment spend
- IndexedDB cache with a 30-day offline retention window
- Data export and deletion endpoints
- English / Yoruba / Hausa / Igbo / Pidgin preference control (translation copy still needs completion)

### Phase 2 core
- Naira care plans seeded at ₦2,000 / ₦5,000 / ₦8,000
- Server-side Paystack initialization with amount derived from the plan record
- Lazy-loaded Paystack InlineJS using `resumeTransaction(accessCode)`
- USSD-only Paystack channel option
- Signed Paystack webhook with amount verification before subscription activation
- Adherence yes/no check-in
- Partner-pharmacy lookup within 5km
- 50 clearly marked demo pharmacies across Lagos, Abuja, Kano and Port Harcourt
- Order endpoint with pickup/delivery choice
- Daily refill cron that sends Termii SMS three days before refill where SMS consent exists
- USSD aggregator flow documented; live short code is intentionally not invented

## Important production boundaries

### Medication safety
Plan drug names represent fulfilment bundles, not prescribing. Medicines that require prescriptions must only be fulfilled against a valid prescription and pharmacist/doctor review. MediNaija does not diagnose or independently change treatment.

### Pharmacy trust
The seeded pharmacies use `DEMO-PCN-xxxx` identifiers. They are test data only. Replace them with verified PCN partner records before public launch.

### Nigerian data residency
For production PII, point `NEXT_PUBLIC_SUPABASE_URL` at a Supabase deployment hosted in Nigeria (for example self-hosted on Nigerian infrastructure such as MainOne or Rack Centre). Do not use a foreign-region database for production PII if the in-country storage rule remains mandatory.

### USSD
Do not hard-code `*737#` as MediNaija's short code. A production USSD code must be issued by the selected aggregator. The repository contains the intended menu contract in `docs/MEDINAIJA_USSD.md`.

## Setup

1. Create or self-host Supabase in the required Nigerian region/infrastructure.
2. Run:
   ```sql
   supabase/migrations/202610030001_medinaija_mvp.sql
   ```
3. Enable phone authentication in Supabase and configure its supported SMS provider.
4. Copy `.env.example` to `.env.local` and add test keys.
5. Install and run:
   ```bash
   npm install
   npm run dev
   ```
6. Run high-risk tests:
   ```bash
   npm test
   ```

## Environment variables

Required for the first vertical slice:

```dotenv
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
PAYSTACK_SECRET_KEY=
PAYSTACK_PUBLIC_KEY=
TERMII_BASE_URL=
TERMII_API_KEY=
TERMII_SENDER_ID=MediNaija
NEXT_PUBLIC_APP_URL=https://your-domain.example
CRON_SECRET=
```

Recommended before public launch:

```dotenv
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=
NEXT_PUBLIC_SENTRY_DSN=
SENTRY_DSN=
OPENAI_API_KEY=
OPENAI_TRIAGE_MODEL=gpt-4o-mini
FLUTTERWAVE_SECRET_KEY=
FLUTTERWAVE_PUBLIC_KEY=
```

## Supabase RLS

The migration enables Row Level Security across patient-owned tables. Patient records use the authenticated Supabase user UUID and policies restrict reads/writes to `auth.uid()`. Plans and pharmacy directories are public-read; backend service operations use the Supabase service role and must remain server-only.

## Payments

The browser sends only a plan slug and chosen checkout channel. The backend fetches the authoritative plan amount from Supabase before initializing Paystack. The webhook:

1. validates `x-paystack-signature`;
2. checks the payment reference;
3. verifies the paid amount matches the stored amount;
4. marks the payment successful;
5. activates/upserts the matching subscription.

Never expose `PAYSTACK_SECRET_KEY` in the browser.

## Refill reminders

Vercel cron calls `/api/cron/refills` each day at 08:00 UTC (09:00 Nigeria time). Only users who explicitly opted into SMS reminders receive a Termii message.

## Mobile

`mobile/` is an Expo shell using the same Supabase phone OTP model and local AsyncStorage. The next mobile increment should reuse the onboarding/domain types in `shared/medinaija-core.ts` and cache the same 30-day dataset.

Run independently:

```bash
cd mobile
npm install
EXPO_PUBLIC_SUPABASE_URL=... EXPO_PUBLIC_SUPABASE_ANON_KEY=... npm start
```

## Vercel

The root `vercel.json` switches the repository to Next.js and keeps the old Python `api/*.py` functions available during migration. Validate the preview branch before merging to production because the existing project previously served the NigerFlora Vite build.

## Not yet production-complete

These listed roadmap items are intentionally not represented as complete yet:
- live Nigerian USSD aggregator provisioning;
- Flutterwave production fallback;
- GIG/Kwik live dispatch APIs;
- full five-language translated copy;
- custom plan clinical workflow;
- Phase 3 AI triage / speech-to-text / agent app / NHIA integration;
- Phase 4 labs / family accounts / WhatsApp / referrals / admin cohort analytics;
- replacement of demo pharmacies with verified PCN partners;
- production penetration testing, clinical governance and incident-response sign-off.

See `docs/DEMO_SCRIPT.md` for the 3-minute demo flow.
