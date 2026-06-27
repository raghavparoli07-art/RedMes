import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from llm.llm_client import call_llm

async def analyze_context_risk(raw_message: str, recipient_name: str, platform: str) -> dict:
    """
    Agent 1: Analyze the raw message for tone, risk level, and whether the situation has escalated.
    """
    prompt = f"""
    You are an expert communication risk analyst.
    Analyze the following message intended for '{recipient_name}' via '{platform}'.

    Message:
    "{raw_message}"

    Output a JSON object exactly matching this structure (and NO other text):
    {{
      "detected_tone": "angry | passive-aggressive | anxious | neutral | etc...",
      "risk_score": <integer from 0 to 100>,
      "risk_reasons": ["reason 1", "reason 2"],
      "escalation_detected": <boolean>,
      "escalation_reason": "<string or null>",
      "recommended_action": "rewrite | pause_and_wait | suggest_call_instead",
      "relationship_type": "boss_or_senior | colleague | friend | family | client_or_customer | unknown",
      "scenario": "complaint | request | apology | disagreement | update | confrontation | general",
      "detected_language": "english | hindi | hinglish | mixed | other",
      "output_language": "english | hindi | hinglish"
    }}

    Rules:
    - Risk score must factor in: aggressive language, sarcasm, excessive capitalization, ultimatums, legal or threat language.
    - If escalation_detected is true, then recommended_action MUST be "pause_and_wait" or "suggest_call_instead".
    - `relationship_type` is inferred from the recipient name AND message content together.
    - Output language rules:
      - platform=email AND relationship=(boss_or_senior | client_or_customer) -> english
      - platform=email AND relationship=(colleague | friend) -> english
      - platform=slack -> english
      - platform=text AND relationship=(friend | family) -> keep same as detected_language (if hindi/hinglish, output hindi/hinglish)
      - platform=text AND relationship=boss_or_senior -> english
      - if input entirely english -> english
    """
    
    response = await call_llm(prompt, json_format=True)
    try:
        # Simple extraction in case there's markdown wrapping
        start = response.find("{")
        end = response.rfind("}") + 1
        clean_json = response[start:end]
        return json.loads(clean_json)
    except json.JSONDecodeError:
        # Fallback if parsing fails
        return {
            "detected_tone": "unknown",
            "risk_score": 0,
            "risk_reasons": ["Failed to parse LLM response"],
            "escalation_detected": False,
            "escalation_reason": None,
            "recommended_action": "rewrite",
            "relationship_type": "unknown",
            "scenario": "general",
            "detected_language": "english",
            "output_language": "english"
        }
