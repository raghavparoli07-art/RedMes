import json
import sys
import os
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from llm.llm_client import call_llm

# ============================================================
#  Agent 1: Context & Risk Analyzer — Gemma 4 Optimized
#  File: agents/context_risk_agent.py  (replace entirely)
# ============================================================
#
#  WHAT CHANGED FROM GEMMA 2 VERSION:
#  ────────────────────────────────────
#  1. SYSTEM BLOCK added at top of prompt. Gemma 4 is trained
#     to follow a clear <system>/<user> split much better than
#     Gemma 2, which worked with freeform prompts.
#
#  2. JSON SCHEMA is now given as a CONCRETE FILLED EXAMPLE,
#     not just field names + types. Gemma 4 copies structure
#     from examples far more reliably than from descriptions.
#
#  3. Added explicit "DO NOT" rules. Gemma 4's agentic design
#     makes it want to reason, explain, and add commentary.
#     We must explicitly forbid that for JSON-only outputs.
#
#  4. Rules are numbered and ordered by priority. Gemma 4
#     processes ordered lists better than bullet soup.
#
#  5. Output language decision tree is now explicit step-by-
#     step logic instead of prose rules. Gemma 4 follows
#     conditional logic much better when it's formatted clearly.
# ============================================================

REQUIRED_KEYS = {
    "detected_tone",
    "risk_score",
    "risk_reasons",
    "escalation_detected",
    "escalation_reason",
    "recommended_action",
    "relationship_type",
    "scenario",
    "detected_language",
    "output_language",
}

HINGLISH_WORDS = {
    "aaj", "kal", "kya", "kaise", "haal", "ghar", "thik", "theek", "hai",
    "nahi", "nahin", "mat", "kar", "karo", "bata", "batao", "chahiye",
    "chutti", "office", "boss", "sir", "madam", "sab", "tere", "mera",
    "meri", "mujhe", "main", "mein", "aana", "jaana", "paisa", "refund",
}


def _fallback_analysis(raw_message: str, recipient_name: str, platform: str, reason: str) -> dict:
    relationship = _infer_relationship(recipient_name, raw_message)
    return _apply_local_risk_overlay(
        {
            "detected_tone": "needs_review",
            "risk_score": 0,
            "risk_reasons": [],
            "escalation_detected": False,
            "escalation_reason": None,
            "recommended_action": "rewrite",
            "relationship_type": relationship,
            "scenario": "general",
            "detected_language": _detect_language(raw_message),
            "output_language": "english",
        },
        raw_message,
        recipient_name,
        platform,
    )


def _detect_language(message: str) -> str:
    if re.search(r"[\u0900-\u097F]", message):
        return "hindi"
    words = set(re.findall(r"[a-zA-Z']+", message.lower()))
    if len(words & HINGLISH_WORDS) >= 2:
        return "hinglish"
    return "english"


def _infer_scenario(message: str) -> str:
    text = message.lower()
    if any(word in text for word in ["invoice", "payment pending", "paid yet", "payment due"]):
        return "complaint"
    if any(word in text for word in ["interview", "resume", "candidate"]):
        return "request"
    if any(word in text for word in ["appointment", "doctor", "dentist"]):
        return "request"
    if any(word in text for word in ["leave", "not coming", "chutti", "chhutti", "office nahi", "office nahin"]):
        return "request"
    if any(word in text for word in ["assigned", "task", "erp", "status", "what the update", "what is the update"]):
        return "task_followup"
    if any(word in text for word in ["salary", "raise", "increment", "compensation"]):
        return "request"
    if any(word in text for word in ["resign", "resignation", "notice period"]):
        return "update"
    if any(word in text for word in ["password", "login", "access", "account locked"]):
        return "request"
    if any(word in text for word in ["report", "review the doc", "document review"]):
        return "request"
    if any(word in text for word in ["bug", "crash", "error", "not working"]):
        return "update"
    if any(word in text for word in ["permission", "approve", "approval"]):
        return "request"
    if any(word in text for word in ["meeting", "call", "schedule", "reschedule"]):
        return "request"
    if any(word in text for word in ["address", "location", "deliver to"]):
        return "request"
    if any(word in text for word in ["birthday", "happy bday", "hbd"]):
        return "general"
    if any(phrase in text for phrase in ["kya haal", "kaise ho", "ghar pe thik", "ghar pe theek", "sab thik", "sab theek"]):
        return "check_in"
    if any(word in text for word in ["refund", "wrong", "charge", "charged", "paisa"]):
        return "complaint"
    if any(word in text for word in ["sorry", "apolog", "maaf", "maf"]):
        return "apology"
    if any(word in text for word in ["disagree", "not realistic", "concern"]):
        return "disagreement"
    if any(word in text for word in ["update", "blocked", "delay", "deadline"]):
        return "update"
    return "general"


def _infer_relationship(recipient_name: str, message: str) -> str:
    text = f"{recipient_name} {message}".lower()
    if any(word in text for word in ["assigned", "task", "erp", "status update", "update on that"]):
        return "colleague"
    if any(word in text for word in ["boss", "manager", "sir", "madam", "senior"]):
        return "boss_or_senior"
    if any(word in text for word in ["client", "customer"]):
        return "client_or_customer"
    if any(word in text for word in ["mom", "dad", "brother", "sister", "family"]):
        return "family"
    if any(word in text for word in ["friend", "bro", "bhai"]):
        return "friend"
    return "unknown"


def _apply_local_risk_overlay(result: dict, raw_message: str, recipient_name: str, platform: str) -> dict:
    text = raw_message.lower()
    relationship = result.get("relationship_type") or _infer_relationship(recipient_name, raw_message)
    result["relationship_type"] = relationship

    reasons = list(result.get("risk_reasons") or [])
    local_score = 0
    local_tone = None

    risk_patterns = [
        (r"\bfired\b|\bfire you\b|\bterminate\b|\btermination\b|\brightaway\b|\bright away\b", 60, "threatening consequence"),
        (r"\btell me\b|\bwhy haven'?t\b|\bnot updated\b|\bnot done\b", 25, "commanding or accusatory wording"),
        (r"\bassigned\b.*\btask\b|\berp\b|\bstatus\b|\bupdate on\b", 15, "work status follow-up"),
        (r"\bfurious\b|\bangry\b|\bmad\b", 45, "angry wording"),
        (r"\bdemand\b|\bright now\b|\btoday\b", 20, "pressure or urgency"),
        (r"\bescalate\b|\bsue\b|\blegal\b|\bcomplaint everywhere\b", 45, "threat or escalation language"),
        (r"\bwrong\b|\brefund\b|\bcharged\b|\bcharge\b", 20, "complaint wording"),
        (r"\bagain\b|\bbecoming a problem\b|\bmissed the deadline\b", 25, "accusatory wording"),
        (r"\bcircus\b", 45, "insulting or contemptuous wording"),
        (r"\bhonestly[, ]", 20, "frustrated framing"),
        (r"\bunacceptable\b|\bdisciplinary action\b", 80, "severe professional warning or threat of disciplinary action"),
        (r"\bnot a request\b", 35, "ultimatum-like wording"),
        (r"\balready decided\b", 25, "closed, non-collaborative framing"),
        (r"\bwhen i'm back\b|\bwhen i am back\b", 15, "dismissive timing"),
        (r"\bwon'?t make the company collapse\b", 45, "sarcastic exaggeration"),
        (r"\bi need a break from\b", 20, "emotionally charged complaint"),
        (r"\bregards\b", 10, "formal sign-off used after a tense message"),
    ]

    for pattern, score, reason in risk_patterns:
        if re.search(pattern, text):
            local_score += score
            if reason not in reasons:
                reasons.append(reason)

    detected_language = _detect_language(raw_message)
    if relationship in {"boss_or_senior", "client_or_customer"}:
        local_score += 20
        if "high-stakes recipient" not in reasons:
            reasons.append("high-stakes recipient")

    if relationship == "boss_or_senior" and detected_language == "hinglish":
        local_score += 15
        if "casual wording for senior recipient" not in reasons:
            reasons.append("casual wording for senior recipient")

    strong_reason_count = len([
        reason for reason in reasons
        if reason not in {"high-stakes recipient", "casual wording for senior recipient"}
    ])

    if detected_language == "hinglish" and relationship == "boss_or_senior" and strong_reason_count == 0:
        local_tone = "informal"
    elif local_score >= 60:
        local_tone = "passive-aggressive"
    elif local_score >= 35:
        local_tone = "frustrated"
    elif result["detected_tone"] in {"unknown", "needs_review"}:
        local_tone = "neutral"

    current_score = int(result.get("risk_score") or 0)
    result["risk_score"] = max(current_score, min(local_score, 95))

    if local_tone and result["detected_tone"] in {"neutral", "unknown", "needs_review"}:
        result["detected_tone"] = local_tone

    if result["risk_score"] >= 70:
        result["escalation_detected"] = True
        result["escalation_reason"] = result.get("escalation_reason") or "The message may damage the relationship if sent as-is."
        result["recommended_action"] = "pause_and_wait"
    elif result["risk_score"] >= 30:
        result["recommended_action"] = "rewrite"

    result["risk_reasons"] = reasons[:5] or ["Local safety check applied."]
    result["detected_language"] = detected_language
    if result.get("scenario") in {None, "general"}:
        result["scenario"] = _infer_scenario(raw_message)
    result["output_language"] = result.get("output_language") or "english"
    return result


# ─────────────────────────────────────────────────────────────
#  GEMMA 4 OPTIMIZED PROMPT BUILDER
# ─────────────────────────────────────────────────────────────
def _build_risk_prompt(raw_message: str, recipient_name: str, platform: str) -> str:
    """
    Builds the Gemma 4 optimized prompt for risk analysis.

    Key differences from the Gemma 2 version:
    - Opens with a clear role declaration (Gemma 4 needs this)
    - Uses a FILLED EXAMPLE schema (not just field names)
    - Has numbered rules in priority order
    - Has explicit DO NOT instructions
    - Output language logic is step-by-step, not prose
    """
    return f"""You are RedMes Risk Analyzer, an expert in communication safety and emotional intelligence.

Your ONLY job is to analyze the message below and return a single JSON object.

---
RECIPIENT: {recipient_name}
PLATFORM: {platform}
MESSAGE:
{raw_message}
---

Return EXACTLY this JSON structure. Fill every field. No markdown. No explanation. No text before or after the JSON.

{{
  "detected_tone": "one of: angry | passive-aggressive | frustrated | anxious | neutral | informal | needs_review",
  "risk_score": 0,
  "risk_reasons": ["reason 1", "reason 2"],
  "escalation_detected": false,
  "escalation_reason": null,
  "recommended_action": "one of: rewrite | pause_and_wait | suggest_call_instead",
  "relationship_type": "one of: boss_or_senior | colleague | subordinate_or_employee | friend | family | client_or_customer | unknown",
  "scenario": "one of: complaint | request | apology | disagreement | update | task_followup | general",
  "detected_language": "one of: english | hindi | hinglish | mixed",
  "output_language": "one of: english | hindi | hinglish"
}}

SCORING RULES (apply in order, add scores together):
1. Words like 'fired', 'terminate', 'right away' → +60 risk
2. 'tell me', 'why haven't you', 'not done' → +25 risk
3. 'furious', 'angry', 'mad' → +45 risk
4. 'demand', 'right now', urgency pressure → +20 risk
5. 'sue', 'legal', 'escalate', 'complaint everywhere' → +45 risk
6. Sarcasm, contempt, insults (e.g. 'circus') → +45 risk
7. 'not a request', 'already decided' → +35 risk
8. Recipient is boss or client → +20 risk
9. Hinglish message to boss or client → +15 additional risk
10. 'unacceptable', 'disciplinary action' → +80 risk

ESCALATION RULES:
- If risk_score >= 70 → escalation_detected must be true, recommended_action must be "pause_and_wait"
- If risk_score >= 30 → recommended_action must be "rewrite"
- If risk_score < 30 → recommended_action is "rewrite" (message can still be improved)

RELATIONSHIP DETECTION:
- Look at BOTH the recipient name AND the message content together
- Words like 'boss', 'sir', 'manager', 'madam', 'senior' → boss_or_senior
- Words like 'client', 'customer' → client_or_customer
- Words like 'friend', 'bro', 'bhai', 'yaar' → friend
- Words like 'mom', 'dad', 'brother', 'sister' → family
- Use context to deduce relationship. (e.g., 'sir', 'mgr' -> boss_or_senior. 'bro', 'yaar' -> friend. 'subordinate', 'employee', stern warnings from boss -> subordinate_or_employee).
- Work context without seniority cues → colleague

OUTPUT LANGUAGE DECISION (follow this exactly):
- Step 1: If platform is email → output_language is always "english"
- Step 2: If platform is slack → output_language is always "english"
- Step 3: If platform is text AND relationship is boss_or_senior → output_language is "english"
- Step 4: If platform is text AND relationship is friend or family AND message is in hindi → output_language is "hindi"
- Step 5: If platform is text AND relationship is friend or family AND message is in hinglish → output_language is "hinglish"
- Step 6: All other cases → output_language is "english"

LANGUAGE DETECTION:
- Devanagari script present → "hindi"
- Roman script with 2+ Hinglish words (kal, aaj, kya, hai, nahi, theek, chutti, karo, etc.) → "hinglish"
- Everything else → "english"

DO NOT add any text before or after the JSON.
DO NOT wrap the JSON in markdown code blocks.
DO NOT add extra fields to the JSON.
DO NOT leave any field as null unless escalation_reason and it is genuinely not applicable.
"""


async def analyze_context_risk(raw_message: str, recipient_name: str, platform: str) -> dict:
    """
    Agent 1: Analyze the raw message for tone, risk level, and escalation.
    Gemma 4 optimized version.
    """
    prompt = _build_risk_prompt(raw_message, recipient_name, platform)

    try:
        response = await call_llm(prompt, json_format=True, creative=False)
    except Exception:
        return _fallback_analysis(raw_message, recipient_name, platform, "AI risk analysis was unavailable.")

    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start == -1 or end == 0:
            return _fallback_analysis(raw_message, recipient_name, platform, "AI returned no JSON for risk analysis.")
        clean_json = response[start:end]
        parsed = json.loads(clean_json)
        if not REQUIRED_KEYS.issubset(parsed):
            return _fallback_analysis(raw_message, recipient_name, platform, "AI risk analysis was incomplete.")
        return _apply_local_risk_overlay(parsed, raw_message, recipient_name, platform)
    except (json.JSONDecodeError, TypeError, ValueError):
        return _fallback_analysis(raw_message, recipient_name, platform, "Failed to parse AI risk analysis.")
