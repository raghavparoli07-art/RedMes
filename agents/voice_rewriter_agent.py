import json
import os
import sys
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from llm.llm_client import call_llm
from mcp_server.redmes_server import mcp
from agents.context_risk_agent import analyze_context_risk

async def run_voice_rewriter(raw_message: str, detected_tone: str, risk_reasons: list, relationship_type: str, scenario: str, output_language: str, platform: str, detected_language: str) -> dict:
    """
    Agent 3: Rewrite message in three distinct tones anchored to user's voice and relationship context.
    """
    # Fetch user voice sample using MCP tool
    voice_samples = mcp._tool_manager.get_tool("get_user_voice_sample").fn()
    samples_str = json.dumps(voice_samples, indent=2)
    
    prompt = f"""
    You are an expert copywriter and communication strategist.
    Your task is to rewrite the following message in three distinct tones: Diplomatic, Direct, and Warm.
    CRITICAL: The rewrites MUST reflect the user's real vocabulary, sentence length, formality level, and common phrases from their voice samples. Do NOT use generic tone-shift templates.

    Context:
    - Relationship: {relationship_type}
    - Scenario: {scenario}
    - Platform: {platform}
    - Target Output Language: {output_language}
    - Original Language: {detected_language}

    User's Voice Samples:
    {samples_str}

    Original Message (Detected tone: {detected_tone}):
    "{raw_message}"

    Risk Reasons to avoid: {json.dumps(risk_reasons)}

    Language rules:
    - Every rewrite MUST be written in the Target Output Language.
    - If Target Output Language is english, write only in English. Do not answer in Hindi or Hinglish.
    - If Target Output Language is hindi, write in natural Hindi.
    - If Target Output Language is hinglish, write in natural Hinglish.
    - If Target Output Language is any other language, translate the meaning into that language.
    - Preserve names, company names, links, numbers, and technical terms when translation would be unnatural.

    Output a JSON object exactly matching this structure (and NO other text):
    {{
      "versions": {{
        "diplomatic": "<string>",
        "direct": "<string>",
        "warm": "<string>"
      }},
      "rewrite_notes": "<string explaining what was changed and why (e.g. 'Translated from Hinglish to professional English. Removed accusatory language.')>"
    }}
    """
    
    response = await call_llm(prompt, json_format=True)
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        clean_json = response[start:end]
        parsed = json.loads(clean_json)
        versions = parsed.get("versions", {})
        rewrite_notes = parsed.get("rewrite_notes", "Adjusted tone for context.")
    except json.JSONDecodeError:
        versions = {
            "diplomatic": "I would like to discuss this further when you have a moment.",
            "direct": "Let's review this together.",
            "warm": "Hope you're doing well! Could we chat about this soon?"
        }
        rewrite_notes = "Adjusted tone for context."
    
    # Ensure all required keys exist
    for key in ["diplomatic", "direct", "warm"]:
        if key not in versions:
            versions[key] = f"Could we revisit this? ({key} fallback)"

    # Compute risk score after by running each rewritten version through context_risk_agent logic
    risk_score_after = {}
    for tone, text in versions.items():
        # Evaluate risk using Agent 1
        risk_result = await analyze_context_risk(text, "recipient", "any")
        risk_score_after[tone] = risk_result.get("risk_score", 0)

    return {
        "detected_language": detected_language,
        "output_language": output_language,
        "relationship_type": relationship_type,
        "scenario": scenario,
        "versions": versions,
        "risk_score_after": risk_score_after,
        "rewrite_notes": rewrite_notes
    }
