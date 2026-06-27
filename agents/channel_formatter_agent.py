import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from llm.llm_client import call_llm

async def run_channel_formatter(chosen_message: str, platform: str, relationship_type: str) -> dict:
    """
    Agent 4: Format the chosen rewrite for the specific platform.
    """
    prompt = f"""
    You are an expert communication formatter.
    Format the following message for the specified platform.
    
    Original Message:
    "{chosen_message}"
    
    Platform: {platform}
    Relationship Type: {relationship_type}
    
    Platform Rules:
    - Email: Add appropriate greeting and sign-off (formal for boss/client, light for others). Slightly more formal structure. Use formatting if helpful.
    - Slack: Shorter, light formatting acceptable. No formal greeting or sign-off.
    - Text: Shortest, casual, no greeting or sign-off.
    
    Output a JSON object exactly matching this structure (and NO other text):
    {{
      "formatted_message": "<string>",
      "platform": "{platform}",
      "notes": "<string explaining what formatting was applied>"
    }}
    """
    
    response = await call_llm(prompt, json_format=True)
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        clean_json = response[start:end]
        return json.loads(clean_json)
    except json.JSONDecodeError:
        return {
            "formatted_message": chosen_message,
            "platform": platform,
            "notes": "Failed to format, returning original."
        }
