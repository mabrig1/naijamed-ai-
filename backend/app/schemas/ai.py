from pydantic import BaseModel
from typing import Literal


class AIRequest(BaseModel):
    prompt: str
    provider: Literal["gemini", "claude"] = "gemini"


class AIResponse(BaseModel):
    response: str
    provider: str
