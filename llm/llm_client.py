import json
import httpx

# Configuration
USE_GEMINI = False  # Set to True to use Gemini API instead of local Ollama
GEMINI_API_KEY = "YOUR_API_KEY_HERE"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma4:12b"

async def call_llm(prompt: str, json_format: bool = True) -> str:
    """Calls the LLM with the given prompt.
    Returns the string response, expecting it to be JSON if json_format is True.
    """
    if USE_GEMINI:
        return await _call_gemini(prompt, json_format)
    else:
        return await _call_ollama(prompt, json_format)

async def _call_ollama(prompt: str, json_format: bool) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }
    if json_format:
        payload["format"] = "json"
        
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(OLLAMA_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
    except httpx.ConnectError:
        # Fallback handling if Ollama is not running
        raise ConnectionError("Ollama is not reachable. Please ensure Ollama is running locally.")
    except Exception as e:
        raise Exception(f"Error calling local LLM: {str(e)}")

async def _call_gemini(prompt: str, json_format: bool) -> str:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    
    # We could use genai.GenerativeModel.generate_content
    # For a real implementation, we'd use gemini-1.5-flash or similar
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    if json_format:
        # Instruction for JSON in prompt since gemini sometimes requires schema for strict JSON
        prompt = f"{prompt}\n\nIMPORTANT: YOU MUST RETURN ONLY VALID JSON."
        
    try:
        response = model.generate_content(prompt)
        text = response.text
        # Strip markdown code blocks if gemini returned them
        if json_format:
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
        return text.strip()
    except Exception as e:
        raise Exception(f"Error calling Gemini API: {str(e)}")
