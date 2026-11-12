import json
from google import genai
from google.genai import types
from app.core.config import settings

def gemini_configured() -> bool:
    return bool(settings.gemini_api_key.strip())

def _client():
    if not gemini_configured():
        raise RuntimeError("Gemini API is not configured. Add GEMINI_API_KEY to your .env file.")
    return genai.Client(api_key=settings.gemini_api_key)

def generate_json(prompt: str) -> dict:
    client = _client()
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.3,
        ),
    )
    text = (response.text or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"AI returned invalid JSON: {exc}")

def generate_text(prompt: str) -> str:
    client = _client()
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.5),
    )
    return (response.text or "").strip()
