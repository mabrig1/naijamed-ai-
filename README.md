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

## License

MIT
