from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_NAME: str = "NaijaMed AI"
    APP_ENV: str = "development"

    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    DATABASE_URL: str = "postgresql://naijamed:naijamed_secret@localhost:5432/naijamed_db"

    # Gemini — accepts both spellings from .env
    GEMINI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""          # legacy alias; gemini service prefers GEMINI_API_KEY

    ANTHROPIC_API_KEY: str = ""
    PAYSTACK_SECRET_KEY: str = ""
    PAYSTACK_BASE_URL: str = "https://api.paystack.co"

    # Flutterwave (used by escrow for NGN/African payments)
    FLUTTERWAVE_SECRET_KEY: str = ""
    FLUTTERWAVE_BASE_URL: str = "https://api.flutterwave.com/v3"
    FLUTTERWAVE_WEBHOOK_SECRET: str = ""   # set in FLW dashboard → Webhooks → Secret hash

    # Stripe (used by escrow for USD/EUR international payments)
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""        # from `stripe listen --print-secret` or dashboard

    # Shipment carrier webhook shared secret (set by your freight partner)
    SHIPMENT_WEBHOOK_SECRET: str = ""

    # ── Email — SendGrid (primary) ────────────────────────────────────────────
    SENDGRID_API_KEY: str = ""

    # ── Email — SMTP fallback ────────────────────────────────────────────────
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587          # TLS/STARTTLS
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    # ── SMS — Termii (Nigerian SMS gateway) ──────────────────────────────────
    TERMII_API_KEY: str = ""
    TERMII_BASE_URL: str = "https://api.ng.termii.com/api"

    # ── Currency conversion — exchangerate-api.com ───────────────────────────
    EXCHANGERATE_API_KEY: str = ""

    # Frontend origin — used in CORS allow list
    FRONTEND_URL: str = "http://localhost:5173"

    # Rate limiting
    AI_RATE_LIMIT: str = "10/minute"
    EXPORT_AI_RATE_LIMIT: str = "5/minute"

    @property
    def effective_gemini_key(self) -> str:
        return self.GEMINI_API_KEY or self.GOOGLE_API_KEY

    @property
    def CORS_ORIGINS(self) -> List[str]:
        origins = {
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            self.FRONTEND_URL,
        }
        return list(origins)


settings = Settings()
