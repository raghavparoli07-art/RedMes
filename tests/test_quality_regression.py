import pytest
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.context_risk_agent import _apply_local_risk_overlay
from agents.context_risk_agent import _detect_language
from agents.voice_rewriter_agent import REQUIRED_VERSION_KEYS
from agents.voice_rewriter_agent import _fallback_versions
from agents.voice_rewriter_agent import run_voice_rewriter


TYPICAL_CASES = [
    {
        "name": "rahul_erp_task_threat_english",
        "message": "Hi Rahul, You have been assigned a task for yesterday not updated on erp tell me what the update on that if it is not done you will be fired rightaway",
        "recipient": "Rahul",
        "platform": "email",
        "relationship": "colleague",
        "scenario": "task_followup",
        "language": "english",
        "min_risk": 80,
        "must_include": ["update"],
    },
    {
        "name": "rahul_erp_task_threat_hindi",
        "message": "Hi Rahul, You have been assigned a task for yesterday not updated on erp tell me what the update on that if it is not done you will be fired rightaway",
        "recipient": "Rahul",
        "platform": "email",
        "relationship": "colleague",
        "scenario": "task_followup",
        "language": "hindi",
        "min_risk": 80,
        "must_include": [],
    },
    {
        "name": "boss_hinglish_checkin_english",
        "message": "or boss kya haal hai ghar pe thik hai tere sab",
        "recipient": "boss",
        "platform": "email",
        "relationship": "boss_or_senior",
        "scenario": "general",
        "language": "english",
        "min_risk": 30,
        "must_include": ["home"],
    },
    {
        "name": "boss_hinglish_checkin_hinglish",
        "message": "or boss kya haal hai ghar pe thik hai tere sab",
        "recipient": "boss",
        "platform": "email",
        "relationship": "boss_or_senior",
        "scenario": "general",
        "language": "hinglish",
        "min_risk": 30,
        "must_include": ["ghar"],
    },
    {
        "name": "boss_hinglish_checkin_hindi",
        "message": "or boss kya haal hai ghar pe thik hai tere sab",
        "recipient": "boss",
        "platform": "email",
        "relationship": "boss_or_senior",
        "scenario": "general",
        "language": "hindi",
        "min_risk": 30,
        "must_include": [],
    },
    {
        "name": "boss_passive_aggressive_leave_hindi",
        "message": "Hi Boss, I'm not coming to work today. Honestly, I need a break from this circus. One day without me won't make the company collapse. I've already decided, so this isn't really a request.",
        "recipient": "boss",
        "platform": "email",
        "relationship": "boss_or_senior",
        "scenario": "request",
        "language": "hindi",
        "min_risk": 80,
        "must_include": [],
    },
    {
        "name": "boss_direct_leave_english",
        "message": "I am taking leave today. Please don't call me unless it is urgent.",
        "recipient": "manager",
        "platform": "email",
        "relationship": "boss_or_senior",
        "scenario": "request",
        "language": "english",
        "min_risk": 20,
        "must_include": ["leave"],
    },
    {
        "name": "client_refund_hindi",
        "message": "This charge is wrong. I need my refund today.",
        "recipient": "client support",
        "platform": "email",
        "relationship": "client_or_customer",
        "scenario": "complaint",
        "language": "hindi",
        "min_risk": 40,
        "must_include": [],
    },
    {
        "name": "colleague_deadline_english",
        "message": "You missed the deadline again. This is becoming a problem.",
        "recipient": "Alex",
        "platform": "slack",
        "relationship": "colleague",
        "scenario": "complaint",
        "language": "english",
        "min_risk": 25,
        "must_include": ["update"],
    },
    {
        "name": "friend_apology_hindi",
        "message": "Sorry I snapped yesterday. I was stressed and should not have spoken like that.",
        "recipient": "friend",
        "platform": "text",
        "relationship": "friend",
        "scenario": "apology",
        "language": "hindi",
        "min_risk": 0,
        "must_include": [],
    },
    {
        "name": "family_boundary_english",
        "message": "I can't come this weekend. Please don't pressure me about it.",
        "recipient": "mom",
        "platform": "text",
        "relationship": "family",
        "scenario": "request",
        "language": "english",
        "min_risk": 0,
        "must_include": ["weekend"],
    },
    {
        "name": "customer_delay_hindi",
        "message": "The delivery is delayed and I need an update today.",
        "recipient": "customer",
        "platform": "email",
        "relationship": "client_or_customer",
        "scenario": "update",
        "language": "hindi",
        "min_risk": 0,
        "must_include": [],
    },
    {
        "name": "boss_disagreement_english",
        "message": "I disagree with this plan because the timeline is not realistic.",
        "recipient": "senior",
        "platform": "email",
        "relationship": "boss_or_senior",
        "scenario": "disagreement",
        "language": "english",
        "min_risk": 0,
        "must_include": ["timeline"],
    },
    {
        "name": "slack_update_hindi",
        "message": "I am blocked on the API issue and need help from backend.",
        "recipient": "team",
        "platform": "slack",
        "relationship": "colleague",
        "scenario": "update",
        "language": "hindi",
        "min_risk": 0,
        "must_include": [],
    },
    {
        "name": "angry_refund_english",
        "message": "I am furious. Refund this now or I will escalate everywhere.",
        "recipient": "support",
        "platform": "email",
        "relationship": "client_or_customer",
        "scenario": "complaint",
        "language": "english",
        "min_risk": 70,
        "must_include": ["refund"],
    },
    {"name": "meeting_schedule_english", "message": "Can we schedule a meeting tomorrow to discuss the launch plan?", "recipient": "Alex", "platform": "slack", "relationship": "colleague", "scenario": "general", "language": "english", "min_risk": 0, "must_include": ["meeting"]},
    {"name": "meeting_schedule_hinglish", "message": "kal launch plan discuss karne ke liye meeting schedule karni hai", "recipient": "team", "platform": "slack", "relationship": "colleague", "scenario": "general", "language": "hinglish", "min_risk": 0, "must_include": ["meeting"]},
    {"name": "invoice_payment_english", "message": "The invoice payment is still pending. Why has it not been paid yet?", "recipient": "vendor", "platform": "email", "relationship": "client_or_customer", "scenario": "complaint", "language": "english", "min_risk": 20, "must_include": ["invoice"]},
    {"name": "invoice_payment_hinglish", "message": "invoice payment abhi tak pending hai status batao", "recipient": "vendor", "platform": "email", "relationship": "client_or_customer", "scenario": "complaint", "language": "hinglish", "min_risk": 20, "must_include": ["invoice"]},
    {"name": "interview_followup_english", "message": "I wanted to check the interview status for my application.", "recipient": "HR", "platform": "email", "relationship": "unknown", "scenario": "request", "language": "english", "min_risk": 0, "must_include": ["interview"]},
    {"name": "salary_discussion_english", "message": "I need to discuss my salary and increment this month.", "recipient": "manager", "platform": "email", "relationship": "boss_or_senior", "scenario": "request", "language": "english", "min_risk": 20, "must_include": ["salary"]},
    {"name": "resignation_english", "message": "I am resigning and need to know the notice period process.", "recipient": "manager", "platform": "email", "relationship": "boss_or_senior", "scenario": "update", "language": "english", "min_risk": 20, "must_include": ["resign"]},
    {"name": "access_issue_english", "message": "My login password is not working and my account is locked.", "recipient": "IT", "platform": "slack", "relationship": "colleague", "scenario": "request", "language": "english", "min_risk": 0, "must_include": ["access"]},
    {"name": "report_review_english", "message": "Please review the report and share feedback by evening.", "recipient": "Priya", "platform": "slack", "relationship": "colleague", "scenario": "request", "language": "english", "min_risk": 0, "must_include": ["report"]},
    {"name": "bug_issue_english", "message": "The dashboard has a bug and the export button is not working.", "recipient": "dev team", "platform": "slack", "relationship": "colleague", "scenario": "update", "language": "english", "min_risk": 0, "must_include": ["bug"]},
    {"name": "permission_request_english", "message": "Please approve my travel permission for Friday.", "recipient": "manager", "platform": "email", "relationship": "boss_or_senior", "scenario": "request", "language": "english", "min_risk": 20, "must_include": ["approve"]},
    {"name": "appointment_english", "message": "I have a doctor appointment tomorrow and need to adjust my schedule.", "recipient": "manager", "platform": "email", "relationship": "boss_or_senior", "scenario": "request", "language": "english", "min_risk": 20, "must_include": ["appointment"]},
    {"name": "address_update_english", "message": "Please deliver to my new address from now on.", "recipient": "support", "platform": "text", "relationship": "client_or_customer", "scenario": "request", "language": "english", "min_risk": 20, "must_include": ["address"]},
    {"name": "birthday_english", "message": "hbd bro have a great one", "recipient": "friend", "platform": "text", "relationship": "friend", "scenario": "general", "language": "english", "min_risk": 0, "must_include": ["birthday"]},
    {"name": "bug_issue_hinglish", "message": "dashboard me bug hai export button work nahi kar raha", "recipient": "dev team", "platform": "slack", "relationship": "colleague", "scenario": "update", "language": "hinglish", "min_risk": 0, "must_include": ["bug"]},
    {"name": "access_issue_hinglish", "message": "mera login access work nahi kar raha password issue hai", "recipient": "IT", "platform": "slack", "relationship": "colleague", "scenario": "request", "language": "hinglish", "min_risk": 0, "must_include": ["access"]},
    {"name": "report_review_hinglish", "message": "report review karke feedback bhej do", "recipient": "Priya", "platform": "slack", "relationship": "colleague", "scenario": "request", "language": "hinglish", "min_risk": 0, "must_include": ["report"]},
    {"name": "salary_discussion_hinglish", "message": "salary increment par discussion karna hai", "recipient": "manager", "platform": "email", "relationship": "boss_or_senior", "scenario": "request", "language": "hinglish", "min_risk": 20, "must_include": ["salary"]},
    {"name": "resignation_hinglish", "message": "main resign kar raha hoon notice period process bata do", "recipient": "manager", "platform": "email", "relationship": "boss_or_senior", "scenario": "update", "language": "hinglish", "min_risk": 20, "must_include": ["resign"]},
    {"name": "birthday_hinglish", "message": "hbd bhai mast birthday enjoy kar", "recipient": "friend", "platform": "text", "relationship": "friend", "scenario": "general", "language": "hinglish", "min_risk": 0, "must_include": ["birthday"]},
    {"name": "invoice_payment_hindi", "message": "The invoice payment is still pending. Why has it not been paid yet?", "recipient": "vendor", "platform": "email", "relationship": "client_or_customer", "scenario": "complaint", "language": "hindi", "min_risk": 20, "must_include": []},
    {"name": "interview_followup_hindi", "message": "I wanted to check the interview status for my application.", "recipient": "HR", "platform": "email", "relationship": "unknown", "scenario": "request", "language": "hindi", "min_risk": 0, "must_include": []},
    {"name": "salary_discussion_hindi", "message": "I need to discuss my salary and increment this month.", "recipient": "manager", "platform": "email", "relationship": "boss_or_senior", "scenario": "request", "language": "hindi", "min_risk": 20, "must_include": []},
    {"name": "access_issue_hindi", "message": "My login password is not working and my account is locked.", "recipient": "IT", "platform": "slack", "relationship": "colleague", "scenario": "request", "language": "hindi", "min_risk": 0, "must_include": []},
    {"name": "bug_issue_hindi", "message": "The dashboard has a bug and the export button is not working.", "recipient": "dev team", "platform": "slack", "relationship": "colleague", "scenario": "update", "language": "hindi", "min_risk": 0, "must_include": []},
    {"name": "appointment_hindi", "message": "I have a doctor appointment tomorrow and need to adjust my schedule.", "recipient": "manager", "platform": "email", "relationship": "boss_or_senior", "scenario": "request", "language": "hindi", "min_risk": 20, "must_include": []},
    {"name": "birthday_hindi", "message": "hbd bro have a great one", "recipient": "friend", "platform": "text", "relationship": "friend", "scenario": "general", "language": "hindi", "min_risk": 0, "must_include": []},
    {"name": "subordinate_warning_english", "message": "You were assigned a task yesterday not updated. This is unacceptable and may lead to disciplinary action.", "recipient": "Rahul", "platform": "email", "relationship": "subordinate_or_employee", "scenario": "task_followup", "language": "english", "min_risk": 80, "must_include": ["unacceptable", "action"]},
    {"name": "subordinate_warning_hinglish", "message": "kal ka task complete nahi hua. ye unacceptable hai aur disciplinary action liya ja sakta hai.", "recipient": "Rahul", "platform": "email", "relationship": "subordinate_or_employee", "scenario": "task_followup", "language": "hinglish", "min_risk": 80, "must_include": ["action"]},
    {"name": "vendor_negotiation_english", "message": "The quote is too high. Can you give a discount to fit our budget?", "recipient": "vendor", "platform": "email", "relationship": "client_or_customer", "scenario": "negotiation", "language": "english", "min_risk": 0, "must_include": ["discount", "budget"]},
    {"name": "vendor_negotiation_hinglish", "message": "price thoda zyada hai discount mil sakta hai kya budget kam hai", "recipient": "vendor", "platform": "email", "relationship": "client_or_customer", "scenario": "negotiation", "language": "hinglish", "min_risk": 0, "must_include": ["budget"]},
    {"name": "colleague_handoff_english", "message": "I am out tomorrow. Can you take over the deployment task?", "recipient": "team", "platform": "slack", "relationship": "colleague", "scenario": "handoff", "language": "english", "min_risk": 0, "must_include": ["take", "over"]},
    {"name": "colleague_handoff_hindi", "message": "I am out tomorrow. Can you take over the deployment task?", "recipient": "team", "platform": "slack", "relationship": "colleague", "scenario": "handoff", "language": "hindi", "min_risk": 0, "must_include": []},
    {"name": "client_apology_english", "message": "We messed up the delivery today. It won't happen again.", "recipient": "client", "platform": "email", "relationship": "client_or_customer", "scenario": "apology", "language": "english", "min_risk": 0, "must_include": ["apologize", "happen"]},
    {"name": "family_emergency_hinglish", "message": "urgent hai jaldi call karo hospital me hai", "recipient": "brother", "platform": "text", "relationship": "family", "scenario": "emergency", "language": "hinglish", "min_risk": 0, "must_include": ["urgent", "call"]},
    {"name": "family_emergency_english", "message": "This is an emergency. Please call me back immediately, we are at the hospital.", "recipient": "sister", "platform": "text", "relationship": "family", "scenario": "emergency", "language": "english", "min_risk": 0, "must_include": ["emergency", "call"]},
    {"name": "friend_cancellation_english", "message": "I can't attend the party tonight, something came up.", "recipient": "friend", "platform": "text", "relationship": "friend", "scenario": "cancellation", "language": "english", "min_risk": 0, "must_include": ["attend"]},
    {"name": "friend_cancellation_hinglish", "message": "aaj party me nahi aa sakta yaar kuch kaam aa gaya", "recipient": "friend", "platform": "text", "relationship": "friend", "scenario": "cancellation", "language": "hinglish", "min_risk": 0, "must_include": ["aa", "nahi"]},
    {"name": "interview_rejection_english", "message": "We cannot move forward with your application at this time.", "recipient": "candidate", "platform": "email", "relationship": "unknown", "scenario": "rejection", "language": "english", "min_risk": 0, "must_include": ["forward", "application"]},
    {"name": "condolence_english", "message": "I am very sorry for your loss. They passed away too soon.", "recipient": "colleague", "platform": "text", "relationship": "colleague", "scenario": "condolence", "language": "english", "min_risk": 0, "must_include": ["sorry", "loss"]},
    {"name": "gentle_reminder_english", "message": "Just sending a gentle reminder to please fill out the survey.", "recipient": "team", "platform": "slack", "relationship": "colleague", "scenario": "reminder", "language": "english", "min_risk": 0, "must_include": ["reminder", "survey"]},
    {"name": "gentle_reminder_hinglish", "message": "ek gentle reminder bhej raha tha survey bhar dena please", "recipient": "team", "platform": "slack", "relationship": "colleague", "scenario": "reminder", "language": "hinglish", "min_risk": 0, "must_include": ["reminder", "survey"]},
]


def _base_risk(case):
    return {
        "detected_tone": "neutral",
        "risk_score": 0,
        "risk_reasons": [],
        "escalation_detected": False,
        "escalation_reason": None,
        "recommended_action": "rewrite",
        "relationship_type": case["relationship"],
        "scenario": case["scenario"],
        "detected_language": "english",
        "output_language": case["language"],
    }


def _has_hindi(text):
    return any("\u0900" <= char <= "\u097F" for char in text)


@pytest.mark.parametrize("case", TYPICAL_CASES, ids=[case["name"] for case in TYPICAL_CASES])
def test_local_risk_overlay_handles_typical_cases(case):
    result = _apply_local_risk_overlay(_base_risk(case), case["message"], case["recipient"], case["platform"])

    assert isinstance(result["risk_score"], int)
    assert result["risk_score"] >= case["min_risk"]
    assert result["risk_reasons"]


def test_detects_roman_hinglish():
    assert _detect_language("or boss kya haal hai ghar pe thik hai tere sab") == "hinglish"


@pytest.mark.parametrize("case", TYPICAL_CASES, ids=[case["name"] for case in TYPICAL_CASES])
@pytest.mark.parametrize("language", ["english", "hinglish", "hindi"])
def test_fallback_templates_are_complete_for_case_intents(case, language):
    versions, notes = _fallback_versions(
        case["message"],
        case["relationship"],
        case["scenario"],
        language,
        case["platform"],
    )

    assert set(versions) == REQUIRED_VERSION_KEYS
    assert notes
    assert all(versions[key].strip() for key in REQUIRED_VERSION_KEYS)
    assert len(set(versions.values())) == 3
    if language == "hindi":
        assert all(_has_hindi(value) for value in versions.values())
    if language == "english":
        assert all(not _has_hindi(value) for value in versions.values())


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_response,language",
    [
        ('{"versions": {"diplomatic": "Same text", "direct": "Same text", "warm": "Same text"}, "rewrite_notes": "bad"}', "english"),
        ('{"versions": {"diplomatic": "[Boss Name], please check", "direct": "Please check", "warm": "Please check kindly"}, "rewrite_notes": "bad"}', "english"),
        ('{"versions": {"diplomatic": "Please check this", "direct": "Check this", "warm": "Please check when free"}, "rewrite_notes": "bad"}', "hindi"),
        ('{"versions": {"diplomatic": "नमस्ते, कृपया जांच करें।", "direct": "जांच करें।", "warm": "कृपया देख लें।"}, "rewrite_notes": "bad"}', "english"),
    ],
)
async def test_invalid_model_outputs_are_replaced(monkeypatch, bad_response, language):
    async def bad_llm(*args, **kwargs):
        return bad_response

    monkeypatch.setattr("agents.voice_rewriter_agent.call_llm", bad_llm)

    result = await run_voice_rewriter(
        raw_message="The dashboard has a bug and the export button is not working.",
        detected_tone="neutral",
        risk_reasons=[],
        relationship_type="colleague",
        scenario="update",
        output_language=language,
        platform="slack",
        detected_language="english",
    )

    values = list(result["versions"].values())
    assert len(set(values)) == 3
    assert all("[" not in value and "]" not in value for value in values)
    if language == "hindi":
        assert all(_has_hindi(value) for value in values)
    if language == "english":
        assert all(not _has_hindi(value) for value in values)
        assert any("bug" in value.lower() for value in values)


@pytest.mark.asyncio
@pytest.mark.parametrize("case", TYPICAL_CASES, ids=[case["name"] for case in TYPICAL_CASES])
async def test_rewriter_fallback_is_precise_distinct_and_language_safe(monkeypatch, case):
    async def broken_llm(*args, **kwargs):
        return '{"versions": {"diplomatic": "Could we revisit this?", "direct": "Could we revisit this?", "warm": "Could we revisit this?"}}'

    monkeypatch.setattr("agents.voice_rewriter_agent.call_llm", broken_llm)

    result = await run_voice_rewriter(
        raw_message=case["message"],
        detected_tone="frustrated",
        risk_reasons=["test risk"],
        relationship_type=case["relationship"],
        scenario=case["scenario"],
        output_language=case["language"],
        platform=case["platform"],
        detected_language="english",
    )

    versions = result["versions"]
    values = [versions["diplomatic"], versions["direct"], versions["warm"]]

    assert len(set(values)) == 3
    assert all("fallback" not in value.lower() for value in values)
    assert all(len(value.split()) <= 45 for value in values)
    assert all("Could we revisit this?" not in value for value in values)

    if case["language"] == "hindi":
        assert all(_has_hindi(value) for value in values)
    if case["language"] == "english":
        assert all(not _has_hindi(value) for value in values)

    for required in case.get("must_include", []):
        assert any(required.lower() in value.lower() for value in values)
