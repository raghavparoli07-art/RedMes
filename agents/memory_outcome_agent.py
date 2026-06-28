import json
import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from llm.llm_client import call_llm
from mcp_server.redmes_server import mcp

# ============================================================
#  Agent 2: Memory & Outcome Analyzer — Gemma 4 Optimized
#  File: agents/memory_outcome_agent.py  (replace entirely)
# ============================================================
#
#  WHAT CHANGED FROM GEMMA 2 VERSION:
#  ────────────────────────────────────
#  1. Prompt is now structured with clear TASK / DATA / RULES /
#     OUTPUT sections. Gemma 4 parses structured prompts much
#     better than the freeform style Gemma 2 accepted.
#
#  2. Added explicit null handling rules. Gemma 4 sometimes
#     outputs "null" as a string ("null") instead of JSON null.
#     We now sanitize this in the response handler.
#
#  3. Added a concrete JSON example so Gemma 4 knows exactly
#     what format is expected, including null field examples.
# ============================================================


# ─────────────────────────────────────────────────────────────
#  GEMMA 4 OPTIMIZED PROMPT BUILDER
# ─────────────────────────────────────────────────────────────
def _build_memory_prompt(recipient_name: str, history_str: str) -> str:
    return f"""You are RedMes Memory Analyzer, an expert in communication pattern analysis.

=== YOUR TASK ===
Analyze the past message history for contact '{recipient_name}' and identify patterns.

=== HISTORY DATA ===
{history_str}

=== WHAT TO LOOK FOR ===
1. Tone pattern: How does this person usually communicate? Formal, casual, tense, warm?
2. Repeat issues: Does the same problem or topic appear 3 or more times? If yes, warn about it.

=== OUTPUT FORMAT ===
Return ONLY this JSON. No markdown. No explanation. Nothing before or after the JSON.

{{
  "past_tone_pattern": "Brief description of the usual tone pattern, or null if not enough data",
  "repeat_issue_warning": "Plain English warning if same topic appears 3+ times, or null if none"
}}

=== EXAMPLES OF VALID OUTPUT ===
Example 1 (pattern found, repeat issue found):
{{
  "past_tone_pattern": "Messages to this contact tend to be tense and task-focused",
  "repeat_issue_warning": "You have mentioned the ERP task status to this contact 4 times this month"
}}

Example 2 (pattern found, no repeat issue):
{{
  "past_tone_pattern": "Communication with this contact is generally polite and professional",
  "repeat_issue_warning": null
}}

Example 3 (not enough data):
{{
  "past_tone_pattern": null,
  "repeat_issue_warning": null
}}

=== RULES ===
1. repeat_issue_warning must be null (not the string "null") if no repeat issue exists.
2. past_tone_pattern must be null (not the string "null") if there is not enough history.
3. Do not invent patterns. Only report what is clearly visible in the data.
4. Keep both fields concise — one sentence each maximum.
5. Do NOT add any fields beyond the two specified above.
"""


def _sanitize_null(value) -> any:
    """Convert the string 'null' to actual Python None."""
    if isinstance(value, str) and value.strip().lower() == "null":
        return None
    return value


async def run_memory_outcome(recipient_name: str) -> dict:
    """
    Agent 2: Look up recipient's history to surface patterns and warnings.
    Gemma 4 optimized version.
    """
    history = mcp._tool_manager.get_tool("get_contact_history").fn(recipient_name)

    if not history:
        return {
            "contact_exists": False,
            "message_count": 0,
            "past_tone_pattern": None,
            "repeat_issue_warning": None,
            "last_outcome": None,
        }

    message_count = len(history)
    last_outcome = history[0].get("outcome", "unknown") if history else None

    history_str = json.dumps(history[:10], indent=2)
    prompt = _build_memory_prompt(recipient_name, history_str)

    response = await call_llm(prompt, json_format=True, creative=False)

    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        clean_json = response[start:end]
        data = json.loads(clean_json)
        # Sanitize "null" strings that Gemma 4 sometimes outputs
        past_tone = _sanitize_null(data.get("past_tone_pattern"))
        repeat_warn = _sanitize_null(data.get("repeat_issue_warning"))
    except (json.JSONDecodeError, TypeError, ValueError):
        past_tone = "Unable to analyze past pattern."
        repeat_warn = None

    return {
        "contact_exists": True,
        "message_count": message_count,
        "past_tone_pattern": past_tone,
        "repeat_issue_warning": repeat_warn,
        "last_outcome": last_outcome,
    }
