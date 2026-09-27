from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "NigerFlora BioSciences"
    APP_ENV: str = "development"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ADMIN_EMAILS: str = ""

    # MongoDB Atlas — production data store for Vercel.
    MONGODB_URI: str = ""
    MONGODB_DB: str = "mabrig_healthos"

    # Legacy SQL setting is retained only so archived modules remain import-compatible.
    # The Vercel production entrypoint does not read or require it.
    DATABASE_URL: str = "postgresql://naijamed:naijamed_secret@localhost:5432/naijamed_db"

    GEMINI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    CLINICAL_LLM_MODEL: str = "gemini-1.5-flash"
    CLINICAL_VISION_MODEL: str = "gemini-1.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "models/text-embedding-004"
    QDRANT_URL: str = ""
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION: str = "healthos_clinical_protocols"
    RAG_SCORE_THRESHOLD: float = 0.72

    PHI_ENCRYPTION_KEY: str = ""
    PHI_KEY_VERSION: str = "v1"
    CLINICAL_UPLOAD_MAX_BYTES: int = 8 * 1024 * 1024
    CLINICAL_AUDIO_MAX_BYTES: int = 15 * 1024 * 1024

    OPENAI_API_KEY: str = ""
    OPENAI_TRANSCRIPTION_MODEL: str = "whisper-1"
    AFRICASTALKING_USERNAME: str = ""
    AFRICASTALKING_API_KEY: str = ""
    AFRICASTALKING_SENDER_ID: str = ""
    NOMINATIM_URL: str = "https://nominatim.openstreetmap.org"

    # Payments — Paystack is the Nigeria-first default; Flutterwave is an optional
    # international checkout path for the bioinformatics storefront.
    PAYSTACK_SECRET_KEY: str = ""
    PAYSTACK_BASE_URL: str = "https://api.paystack.co"
    FLUTTERWAVE_SECRET_KEY: str = ""
    FLUTTERWAVE_BASE_URL: str = "https://api.flutterwave.com"
    CONSULT_PLATFORM_FEE_PERCENT: int = 18
    FAMILY_PASS_MONTHLY_KOBO: int = 500_000
    FAMILY_PASS_PAYSTACK_PLAN_CODE: str = ""
    DOCTOR_WORKSPACE_MONTHLY_KOBO: int = 1_500_000
    DOCTOR_WORKSPACE_PAYSTACK_PLAN_CODE: str = ""

    # Formulary postgraduate pharmaceutical research workspace.
    FORMULARY_STUDENT_MONTHLY_KOBO: int = 800_000
    FORMULARY_STUDENT_PAYSTACK_PLAN_CODE: str = ""
    FORMULARY_FREE_REVIEW_LIMIT: int = 2
    FORMULARY_FREE_PAPER_LIMIT: int = 10
    FORMULARY_FREE_PK_RUN_LIMIT: int = 3
    FORMULARY_FREE_PORTFOLIO_ITEM_LIMIT: int = 25
    FORMULARY_FREE_COPILOT_WORKSPACE_LIMIT: int = 1
    FORMULARY_FREE_COPILOT_DRAFT_LIMIT: int = 3
    FORMULARY_PDF_MAX_BYTES: int = 12 * 1024 * 1024
    FORMULARY_LLM_MODEL: str = ""
    OPENALEX_API_KEY: str = ""
    CROSSREF_MAILTO: str = ""

    FRONTEND_URL: str = "https://nigerflora.mabrigkorie.org"
    EXTRA_CORS_ORIGINS: str = "https://nigerflora-biosciences.vercel.app"

    @property
    def effective_gemini_key(self) -> str:
        return self.GEMINI_API_KEY or self.GOOGLE_API_KEY

    @property
    def CORS_ORIGINS(self) -> List[str]:
        origins = {
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "https://nigerflora.mabrigkorie.org",
            "https://nigerflora-biosciences.vercel.app",
            self.FRONTEND_URL,
        }
        if self.EXTRA_CORS_ORIGINS:
            for origin in self.EXTRA_CORS_ORIGINS.split(","):
                if origin.strip():
                    origins.add(origin.strip())
        return list(origins)


settings = Settings()
