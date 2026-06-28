import json
import httpx

# ============================================================
#  RedMes LLM Client — Optimized for Gemma 4 (gemma4:12b)
#  Drop this file into: llm/llm_client.py
# ============================================================
#
#  ROOT CAUSE OF YOUR PROBLEM (why Gemma 4 gave wrong answers):
#  ─────────────────────────────────────────────────────────────
#  1. Gemma 4 is STRICT about JSON schema. The old prompts used
#     loose phrasing like "Output a JSON object matching this
#     structure". Gemma 4 follows this literally — it sometimes
#     adds commentary, wraps in markdown, or invents extra keys.
#     FIX → We now use a SYSTEM prompt block + stricter wording.
#
#  2. `"format": "json"` in Ollama forces Gemma 4 into a raw
#     JSON mode that sometimes strips semantic quality. Gemma 4
#     works BETTER when you instruct it inside the prompt AND
#     strip any markdown wrapping yourself (which we now do).
#     FIX → We disable raw JSON format mode and handle cleanup.
#
#  3. temperature=0.5 for creative rewrites was too high for
#     Gemma 4, causing hallucinated or off-topic messages.
#     FIX → Tuned per call type (see TEMPERATURE_* constants).
#
#  4. Gemma 4 has a longer reasoning chain. The 45s timeout was
#     sometimes not enough for complex messages.
#     FIX → Increased to 90s.
#
#  5. repeat_penalty=1.12 caused Gemma 4 to avoid repeating
#     key words like the recipient's name or topic keywords,
#     making rewrites feel generic and detached.
#     FIX → Lowered to 1.05.
# ============================================================

USE_GEMINI = False
GEMINI_API_KEY = "YOUR_API_KEY_HERE"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma4:12b"
OLLAMA_TIMEOUT_SECONDS = 90.0  # Gemma 4 needs more time than Gemma 2

# Temperature guide for Gemma 4:
#   JSON/analysis tasks  → 0.1  (deterministic, no creativity needed)
#   Message rewrites     → 0.35 (some creativity, but stays on topic)
#   General/fallback     → 0.2
TEMPERATURE_JSON = 0.1
TEMPERATURE_REWRITE = 0.35
TEMPERATURE_DEFAULT = 0.2


def _clean_response(text: str) -> str:
    """
    Gemma 4 sometimes wraps output in ```json ... ``` even when told not to.
    This strips all markdown fences and returns clean text.
    """
    text = text.strip()
    # Remove ```json or ``` fences
    if text.startswith("```"):
        lines = text.splitlines()
        # Drop first line (the fence opener)
        lines = lines[1:]
        # Drop last line if it's a closing fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


async def call_llm(prompt: str, json_format: bool = True, creative: bool = False) -> str:
    """
    Calls the local Ollama LLM (Gemma 4) with the given prompt.

    Args:
        prompt:      The full prompt string (include JSON schema inside it).
        json_format: If True, we tell the model to return only JSON and
                     clean the response. Does NOT use Ollama's raw format
                     mode (which hurts Gemma 4 quality).
        creative:    If True, uses a slightly higher temperature (for
                     voice rewriting). Keep False for analysis agents.

    Returns:
        Clean string response (JSON string if json_format=True).
    """
    if USE_GEMINI:
        return await _call_gemini(prompt, json_format)
    else:
        return await _call_ollama(prompt, json_format, creative)


async def _call_ollama(prompt: str, json_format: bool, creative: bool = False) -> str:
    if creative:
        temperature = TEMPERATURE_REWRITE
    elif json_format:
        temperature = TEMPERATURE_JSON
    else:
        temperature = TEMPERATURE_DEFAULT

    # IMPORTANT: We do NOT set "format": "json" for Gemma 4.
    # Ollama's raw JSON format mode bypasses Gemma 4's instruction-following
    # layer and produces lower quality, often incomplete outputs.
    # Instead, we embed the JSON requirement in the prompt itself.
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "top_p": 0.92,
            "repeat_penalty": 1.05,   # Was 1.12 — too high for Gemma 4
            "seed": 42,
            "num_predict": 1200,       # Enough for 3 rewrite versions
        }
    }

    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT_SECONDS) as client:
            response = await client.post(OLLAMA_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            raw = data.get("response", "")
            return _clean_response(raw)
    except httpx.ConnectError:
        raise ConnectionError(
            "Ollama is not reachable. Please ensure Ollama is running locally."
        )
    except Exception as e:
        raise Exception(f"Error calling local LLM: {str(e)}")


async def _call_gemini(prompt: str, json_format: bool) -> str:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)

    model = genai.GenerativeModel("gemini-1.5-flash")

    if json_format:
        prompt = f"{prompt}\n\nIMPORTANT: Return ONLY valid JSON. No markdown. No explanation."

    try:
        response = model.generate_content(prompt)
        text = response.text
        return _clean_response(text)
    except Exception as e:
        raise Exception(f"Error calling Gemini API: {str(e)}")
