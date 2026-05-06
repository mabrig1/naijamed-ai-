from ..core.config import settings


def get_gemini_client():
    import google.generativeai as genai
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    return genai.GenerativeModel("gemini-1.5-pro")


def get_claude_client():
    import anthropic
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


async def analyze_herb_gemini(herb_name: str, description: str) -> str:
    model = get_gemini_client()
    prompt = (
        f"You are a pharmaceutical research assistant specializing in Nigerian herbal medicine.\n"
        f"Analyze the herb '{herb_name}'.\nDescription: {description}\n\n"
        "Provide: active compounds, medicinal uses, safety notes, and pharmaceutical potential. "
        "Be concise and scientifically grounded."
    )
    response = model.generate_content(prompt)
    return response.text


async def analyze_herb_claude(herb_name: str, description: str) -> str:
    client = get_claude_client()
    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": (
                    f"You are a pharmaceutical research assistant specializing in Nigerian herbal medicine.\n"
                    f"Analyze the herb '{herb_name}'.\nDescription: {description}\n\n"
                    "Provide: active compounds, medicinal uses, safety notes, and pharmaceutical potential. "
                    "Be concise and scientifically grounded."
                ),
            }
        ],
    )
    return message.content[0].text
