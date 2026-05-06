# NaijaMed AI

> An all-in-one AI-powered platform connecting Nigerian herbal knowledge to pharmaceutical production — from soil to science to pharmacy.

NaijaMed AI bridges centuries of indigenous Nigerian herbal medicine with modern pharmaceutical science, leveraging large language models (Google Gemini and Anthropic Claude) to digitize, validate, and productionize traditional remedies for the global market.

## Monorepo Structure

```
naijamed-ai/
├── frontend/        # React + Vite + TypeScript UI
├── backend/         # FastAPI + PostgreSQL REST API
├── shared/          # Shared types and constants
└── docker-compose.yml
```

## Quick Start

### 1. Start the database

```bash
docker compose up -d
```

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

## Tech Stack

| Layer     | Technology                              |
|-----------|-----------------------------------------|
| Frontend  | React 18, Vite, TypeScript, TailwindCSS |
| State     | React Query v5, React Router v6         |
| Backend   | FastAPI, SQLAlchemy 2, Pydantic v2      |
| Database  | PostgreSQL 16                           |
| Auth      | JWT (python-jose + passlib)             |
| AI        | Google Gemini, Anthropic Claude         |

## Export & Logistics Engine

NaijaMed AI includes a full-stack **Export Hub** enabling Nigerian herbal medicine producers to reach verified global buyers — with end-to-end compliance, logistics, and payment protection built in.

### Features

| Module | Description |
|---|---|
| **Export Marketplace** | Browse and list NAFDAC/NEPC/NAQS-certified herb export listings with grade, origin, HS code, and freight options |
| **Global Buyer Profiles** | Verified international buyers (UK, EU, UAE, USA, Canada, India) with preferred herbs, volume, and incoterms |
| **Freight Calculator** | AI-powered multi-carrier quote engine (sea, air, road, ecommerce) with cost breakdown and transit times |
| **Shipment Tracker** | Real-time cold-chain tracking with temperature monitoring, event timeline, and customs status |
| **Document Vault** | Secure storage for Bills of Lading, NAFDAC certs, NEPC NOECs, packing lists, and customs declarations |
| **Customs Assistant** | HS code lookup for 30+ Nigerian herbs, NCSW SAD form generation, and AI-powered customs Q&A |
| **Price Intelligence** | Live export price index (5 global regions × 20+ herbs), AI 90-day forecasts, and price alert subscriptions |
| **Escrow** | Buyer-seller escrow with Flutterwave (NGN) + Stripe (USD) — 7-day auto-release, dispute resolution with AI advisory |
| **NEPC Integration** | Mock NEPC exporter registration checker and NOEC (Non-Oil Export Certificate) draft generator |
| **NCS / NCSW Integration** | Mock Nigerian Customs Service HS code lookup, duty calculator, and SAD form draft generator |
| **CBN FX Guide** | Central Bank of Nigeria Form NXP repatriation guide — 100% FX repatriation rules, bank list, penalties |
| **Currency Conversion** | Live USD ↔ NGN via exchangerate-api.com with 6-hour cache; NGN equivalent shown on all listings |
| **Notifications** | Email (SendGrid + SMTP fallback) + SMS (Termii API) for orders, shipments, customs clearance, and price alerts |
| **Export Analytics** | Admin dashboard: top herbs, top markets, monthly revenue, and platform commission (2.5%) |

### Environment Variables (Export Engine)

Add these to your `.env` file:

```dotenv
# Email
SENDGRID_API_KEY=your_sendgrid_key
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=app_password

# SMS (Nigeria)
TERMII_API_KEY=your_termii_key
TERMII_BASE_URL=https://api.ng.termii.com/api

# Currency
EXCHANGERATE_API_KEY=your_exchangerate_api_key

# Payment gateways
FLUTTERWAVE_SECRET_KEY=FLWSECK_TEST-...
FLUTTERWAVE_WEBHOOK_SECRET=your_webhook_hash
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### API Endpoints (Export Engine)

All export engine routes are under the protected `/api` namespace:

```
/api/export/*           Export marketplace CRUD, buyer inquiries, AI matching
/api/logistics/*        Freight quotes, shipment tracking, document management
/api/customs/*          HS code lookup, customs chat, NEPC guide, CBN FX guide
/api/prices/*           Price index, forecasts (rate-limited 5/min), alerts
/api/escrow/*           Hold, release, dispute (rate-limited 5/min)
/api/admin/export/*     Analytics: stats, top-herbs, top-markets, revenue
```

### Regulatory Compliance Stack

| Agency | Purpose | Integration |
|---|---|---|
| **NAFDAC** | Product registration | AI-assisted document generation |
| **NEPC** | Export certification (NOEC) | Mock API; real endpoint TBD |
| **NCS / NCSW** | Customs clearance (SAD form) | Mock API; HS code DB + duty calculator |
| **NAQS** | Agricultural quarantine | Certificate reference on listings |
| **CBN** | FX repatriation (Form NXP) | Structured guide with bank contacts |
| **SON** | Standards certification | Referenced in NEPC registration guide |

## License

MIT
