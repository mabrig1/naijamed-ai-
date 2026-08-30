from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "Mabrig HealthOS"
    APP_ENV: str = "development"

    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    DATABASE_URL: str = "postgresql://naijamed:naijamed_secret@localhost:5432/naijamed_db"

    # General AI
    GEMINI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # Clinical AI / RAG
    CLINICAL_LLM_MODEL: str = "gemini-1.5-flash"
    CLINICAL_VISION_MODEL: str = "gemini-1.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "models/text-embedding-004"
    QDRANT_URL: str = ""
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION: str = "healthos_clinical_protocols"
    RAG_SCORE_THRESHOLD: float = 0.72

    # PHI encryption / privacy
    PHI_ENCRYPTION_KEY: str = ""
    PHI_KEY_VERSION: str = "v1"
    CLINICAL_UPLOAD_MAX_BYTES: int = 8 * 1024 * 1024
    CLINICAL_AUDIO_MAX_BYTES: int = 15 * 1024 * 1024

    # Voice + low bandwidth channels
    OPENAI_API_KEY: str = ""
    OPENAI_TRANSCRIPTION_MODEL: str = "whisper-1"
    AFRICASTALKING_USERNAME: str = ""
    AFRICASTALKING_API_KEY: str = ""
    AFRICASTALKING_SENDER_ID: str = ""

    # Geospatial discovery. Public Nominatim is suitable for low-volume pilot use only;
    # production operators should configure a hosted/commercial OSM-compatible endpoint.
    NOMINATIM_URL: str = "https://nominatim.openstreetmap.org"

    # Payments
    PAYSTACK_SECRET_KEY: str = ""
    PAYSTACK_BASE_URL: str = "https://api.paystack.co"
    CONSULT_PLATFORM_FEE_PERCENT: int = 18
    FAMILY_PASS_MONTHLY_KOBO: int = 500_000
    FAMILY_PASS_PAYSTACK_PLAN_CODE: str = ""
    DOCTOR_WORKSPACE_MONTHLY_KOBO: int = 1_500_000
    DOCTOR_WORKSPACE_PAYSTACK_PLAN_CODE: str = ""

    # Flutterwave / Stripe retained for existing marketplace and future enterprise billing
    FLUTTERWAVE_SECRET_KEY: str = ""
    FLUTTERWAVE_BASE_URL: str = "https://api.flutterwave.com/v3"
    FLUTTERWAVE_WEBHOOK_SECRET: str = ""
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    SHIPMENT_WEBHOOK_SECRET: str = ""

    SENDGRID_API_KEY: str = ""
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    TERMII_API_KEY: str = ""
    TERMII_BASE_URL: str = "https://api.ng.termii.com/api"
    EXCHANGERATE_API_KEY: str = ""

    FRONTEND_URL: str = "http://localhost:5173"
    AI_RATE_LIMIT: str = "10/minute"
    EXPORT_AI_RATE_LIMIT: str = "5/minute"

    @property
    def effective_gemini_key(self) -> str:
        return self.GEMINI_API_KEY or self.GOOGLE_API_KEY

    EXTRA_CORS_ORIGINS: str = ""

    @property
    def CORS_ORIGINS(self) -> List[str]:
        origins = {
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "https://nigerflora-biosciences.vercel.app",
            "https://nigerflora.mabrigkorie.org",
            self.FRONTEND_URL,
        }
        if self.EXTRA_CORS_ORIGINS:
            for origin in self.EXTRA_CORS_ORIGINS.split(","):
                if origin.strip():
                    origins.add(origin.strip())
        return list(origins)


settings = Settings()
