from fastapi import APIRouter, Depends, HTTPException

from app.core.security import get_current_user
from app.core.config import settings
from app.models.user import User
from app.schemas.ai import AIRequest, AIResponse

router = APIRouter()

SYSTEM_PROMPT = (
    "You are NigerFlora BioSciences, an expert assistant specialising in Nigerian medicinal plants, "
    "phytochemistry, ethnobotany, and pharmaceutical formulation from herbal sources. "
    "Provide accurate, evidence-based information and note when scientific consensus is limited."
)


def _ask_gemini(prompt: str) -> str:
    key = settings.effective_gemini_key
    if not key:
        raise HTTPException(status_code=503, detail="Gemini API key not configured. Set GEMINI_API_KEY or GOOGLE_API_KEY in .env.")
    import google.generativeai as genai
    genai.configure(api_key=key)
    model = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=SYSTEM_PROMPT)
    return model.generate_content(prompt).text


def _ask_claude(prompt: str) -> str:
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="Anthropic API key not configured")
    import anthropic
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


@router.post("/ask", response_model=AIResponse)
def ask_ai(body: AIRequest, _: User = Depends(get_current_user)):
    try:
        text = _ask_gemini(body.prompt) if body.provider == "gemini" else _ask_claude(body.prompt)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return AIResponse(response=text, provider=body.provider)
