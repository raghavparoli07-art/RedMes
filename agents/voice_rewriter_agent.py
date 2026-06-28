import json
import os
import re
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from llm.llm_client import call_llm
from mcp_server.redmes_server import mcp
from agents.context_risk_agent import _apply_local_risk_overlay

# ============================================================
#  Agent 3: Voice Rewriter — Gemma 4 Optimized
#  File: agents/voice_rewriter_agent.py  (replace entirely)
# ============================================================
#
#  WHAT CHANGED FROM GEMMA 2 VERSION:
#  ────────────────────────────────────
#  1. PROMPT RESTRUCTURED with clear labeled sections.
#     Gemma 4 performs significantly better when the prompt
#     has clear section headers (TASK, CONTEXT, RULES, OUTPUT).
#
#  2. CONCRETE EXAMPLES added for each tone. Gemma 2 could
#     infer tone from labels. Gemma 4 needs to see what
#     "Diplomatic" vs "Direct" vs "Warm" actually looks like.
#
#  3. ANTI-HALLUCINATION FENCE: We now explicitly tell the
#     model what the user's real intent is (extracted from
#     the scenario), so it cannot drift to a different topic.
#
#  4. call_llm now called with creative=True so the rewriter
#     gets a slightly higher temperature than analysis agents,
#     which produces more natural-sounding rewrites.
#
#  5. LENGTH GUIDANCE added per relationship type. Gemma 4
#     tends to write very long messages without this.
# ============================================================

REQUIRED_VERSION_KEYS = {"diplomatic", "direct", "warm"}

HINGLISH_WORDS = {
    "aaj", "kal", "kya", "kaise", "haal", "ghar", "thik", "theek", "hai",
    "nahi", "nahin", "mat", "kar", "karo", "bata", "batao", "chahiye",
    "chutti", "office", "boss", "sir", "madam", "sab", "tere", "mera",
    "meri", "mujhe", "main", "mein", "aana", "jaana", "paisa", "refund",
}


def _normalize(value: str) -> str:
    return (value or "").strip().lower()


def _extract_json_object(response: str) -> dict:
    start = response.find("{")
    end = response.rfind("}") + 1
    if start == -1 or end == 0 or end <= start:
        raise ValueError("No JSON object found.")
    return json.loads(response[start:end])


def _has_devanagari(text: str) -> bool:
    return bool(re.search(r"[\u0900-\u097F]", text or ""))


def _has_hinglish(text: str) -> bool:
    words = set(re.findall(r"[a-zA-Z']+", _normalize(text)))
    return len(words & HINGLISH_WORDS) >= 2


def _is_valid_versions(versions: dict, output_language: str) -> bool:
    if not isinstance(versions, dict) or not REQUIRED_VERSION_KEYS.issubset(versions):
        return False

    values = [str(versions[key]).strip() for key in ["diplomatic", "direct", "warm"]]
    if any(not value for value in values):
        return False
    if len(set(values)) < 3:
        return False
    if any("fallback" in value.lower() for value in values):
        return False
    if any("could we revisit this" in value.lower() for value in values):
        return False
    if any("[" in value or "]" in value for value in values):
        return False

    language = _normalize(output_language)
    if language == "hindi" and any(not _has_devanagari(value) for value in values):
        return False
    if language == "english" and any(_has_devanagari(value) for value in values):
        return False
    return True


def _intent_summary(raw_message: str, scenario: str) -> str:
    lowered = _normalize(raw_message)
    if any(word in lowered for word in ["invoice", "payment pending", "paid yet", "payment due"]):
        return "invoice_payment"
    if any(word in lowered for word in ["interview", "resume", "candidate"]):
        return "interview"
    if any(word in lowered for word in ["appointment", "doctor", "dentist"]):
        return "appointment"
    if any(word in lowered for word in ["handover", "take over", "transfer ownership"]):
        return "handoff"
    if any(word in lowered for word in ["assigned", "erp", "status", "what the update", "what is the update", "not updated", "not done"]):
        return "task_followup"
    if any(word in lowered for word in ["task"]):
        return "task_assignment"
    if any(word in lowered for word in ["salary", "raise", "increment", "compensation"]):
        return "salary"
    if any(word in lowered for word in ["resign", "resignation", "notice period"]):
        return "resignation"
    if any(word in lowered for word in ["password", "login", "access", "account locked"]):
        return "access_issue"
    if any(word in lowered for word in ["report", "review the doc", "document review"]):
        return "report_review"
    if any(word in lowered for word in ["bug", "crash", "error", "not working"]):
        return "bug_issue"
    if any(word in lowered for word in ["interview"]):
        return "interview"
    if any(word in lowered for word in ["invoice", "payment", "paid"]):
        return "invoice"
    if any(word in lowered for word in ["urgent", "emergency", "hospital"]):
        return "emergency"
    if any(word in lowered for word in ["permission", "approve", "approval"]):
        return "permission_request"
    if any(word in lowered for word in ["meeting", "schedule", "reschedule"]):
        return "meeting"
    if any(word in lowered for word in ["address", "location", "deliver to"]):
        return "address_update"
    if any(word in lowered for word in ["birthday", "happy bday", "hbd"]):
        return "birthday"
    if any(word in lowered for word in ["thank", "thanks", "appreciate", "grateful"]):
        return "thanks"
    if any(word in lowered for word in ["sorry for your loss", "condolence", "passed away", "death"]):
        return "condolence"
    if any(word in lowered for word in ["reject", "not selected", "can't move forward", "cannot move forward"]):
        return "rejection"
    if any(word in lowered for word in ["cancel", "cancellation", "can't attend", "cannot attend"]):
        return "cancellation"
    if any(word in lowered for word in ["reminder", "remind", "gentle reminder"]):
        return "reminder"
    if any(word in lowered for word in ["management", "raise this", "escalate this", "escalating this"]):
        return "escalation"
    if any(word in lowered for word in ["negotiate", "discount", "price", "budget"]):
        return "negotiation"
    if any(word in lowered for word in ["performance", "improve", "warning", "quality issue"]):
        return "performance_warning"
    if any(phrase in lowered for phrase in ["kya haal", "kaise ho", "ghar pe thik", "ghar pe theek", "sab thik", "sab theek"]):
        return "check_in"
    if any(word in lowered for word in ["refund", "money back", "charged", "charge", "paisa"]):
        return "refund"
    if any(word in lowered for word in ["deadline", "late", "delay", "delayed", "blocked", "blocker"]):
        return "delay"
    if any(word in lowered for word in ["call me", "call back"]):
        return "call_request"
    if any(word in lowered for word in ["sorry", "apolog", "maaf", "maf"]):
        return "apology"
    if any(word in lowered for word in ["weekend", "pressure", "can't come", "cannot come"]):
        return "boundary"
    if any(word in lowered for word in ["disagree", "not realistic", "concern"]):
        return "disagreement"
    return scenario or "general"


def _hi(text_key: str) -> str:
    phrases = {
        "check_d": "\u0928\u092e\u0938\u094d\u0924\u0947, \u0906\u0936\u093e \u0939\u0948 \u0906\u092a \u0920\u0940\u0915 \u0939\u0948\u0902\u0964 \u092e\u0948\u0902 \u092c\u0938 \u092f\u0939 \u092a\u0942\u091b\u0928\u093e \u091a\u093e\u0939\u0924\u093e \u0925\u093e \u0915\u093f \u0918\u0930 \u092a\u0930 \u0938\u092c \u0920\u0940\u0915 \u0939\u0948 \u092f\u093e \u0928\u0939\u0940\u0902\u0964",
        "check_x": "\u0928\u092e\u0938\u094d\u0924\u0947, \u0918\u0930 \u092a\u0930 \u0938\u092c \u0920\u0940\u0915 \u0939\u0948? \u0915\u0943\u092a\u092f\u093e \u092c\u0924\u093e \u0926\u0940\u091c\u093f\u090f\u0964",
        "check_w": "\u0928\u092e\u0938\u094d\u0924\u0947, \u0906\u092a\u0915\u093e \u0939\u093e\u0932 \u091a\u093e\u0932 \u092a\u0942\u091b\u0928\u093e \u0925\u093e\u0964 \u0906\u0936\u093e \u0939\u0948 \u0918\u0930 \u092a\u0930 \u0938\u092c \u0920\u0940\u0915 \u0939\u094b\u0917\u093e\u0964",
        "generic_d": "\u0928\u092e\u0938\u094d\u0924\u0947, \u092e\u0948\u0902 \u0907\u0938 \u092c\u093e\u0924 \u0915\u094b \u0936\u093e\u0902\u0924 \u0924\u0930\u0940\u0915\u0947 \u0938\u0947 \u0930\u0916\u0928\u093e \u091a\u093e\u0939\u0924\u093e \u0939\u0942\u0902\u0964 \u0915\u0943\u092a\u092f\u093e \u0905\u092a\u0928\u0940 \u0930\u093e\u092f \u092c\u0924\u093e\u090f\u0902\u0964",
        "generic_x": "\u0928\u092e\u0938\u094d\u0924\u0947, \u092e\u0941\u091d\u0947 \u0907\u0938 \u0935\u093f\u0937\u092f \u092a\u0930 \u092c\u093e\u0924 \u0915\u0930\u0928\u0940 \u0939\u0948\u0964 \u0915\u0943\u092a\u092f\u093e \u092c\u0924\u093e\u090f\u0902 \u0906\u0917\u0947 \u0915\u0948\u0938\u0947 \u092c\u0922\u093c\u0947\u0902\u0964",
        "generic_w": "\u0928\u092e\u0938\u094d\u0924\u0947, \u0906\u0936\u093e \u0939\u0948 \u0906\u092a \u0920\u0940\u0915 \u0939\u0948\u0902\u0964 \u092e\u0948\u0902 \u0907\u0938 \u092c\u093e\u0924 \u092a\u0930 \u0906\u092a\u0915\u0940 \u0930\u093e\u092f \u091c\u093e\u0928\u0928\u093e \u091a\u093e\u0939\u0924\u093e \u0939\u0942\u0902\u0964",
        "notes": "\u0938\u0902\u0926\u0947\u0936 \u0915\u094b \u091b\u094b\u091f\u093e, \u0938\u093e\u092b \u0914\u0930 \u0938\u092e\u094d\u092e\u093e\u0928\u091c\u0928\u0915 \u092c\u0928\u093e\u092f\u093e \u0917\u092f\u093e\u0964",
    }
    return phrases.get(text_key, "")


def _fallback_versions(raw_message: str, relationship_type: str, scenario: str, output_language: str, platform: str) -> tuple[dict, str]:
    language = _normalize(output_language)
    intent = _intent_summary(raw_message, scenario)

    english = {
        "check_in": {"diplomatic": "Hi, I hope you are doing well. I just wanted to check if everything is okay at home.", "direct": "Hi, is everything okay at home? Please let me know.", "warm": "Hi, hope all is well. I was just checking in to see if everything is okay at home."},
        "leave_today": {"diplomatic": "Hi, I will not be able to come to work today. Please approve my leave for the day.", "direct": "Hi, I am taking leave today and will resume work tomorrow.", "warm": "Hi, I am not feeling up to work today, so I need to take leave. Sorry for the inconvenience."},
        "task_followup": {"diplomatic": "Hi, could you please share the latest update on the task assigned yesterday? We need to ensure there is no disciplinary action or unacceptable delay.", "direct": "Hi, please update me on the task assigned yesterday. This delay is unacceptable and may lead to disciplinary action.", "warm": "Hi, just checking in on yesterday's task. Please share the current status when you can, to avoid any action."},
        "task_assignment": {"diplomatic": "Hi, please find the details for the upcoming task.", "direct": "Here is the new task assignment.", "warm": "Hi! Just sharing the details for your new task."},
        "salary": {"diplomatic": "I would like to request a discussion regarding my salary and compensation.", "direct": "I need to discuss my salary increment.", "warm": "I was hoping we could schedule some time to discuss my salary and progress."},
        "resignation": {"diplomatic": "Please accept this as formal notice that I will resign from my position.", "direct": "I am resigning from my position effective immediately.", "warm": "It is with a heavy heart that I must resign from my role here."},
        "access_issue": {"diplomatic": "I am currently experiencing an access issue with my account and need assistance.", "direct": "My account access is locked, please reset my password.", "warm": "Hi team, I seem to be locked out of my account and need access, could you help?"},
        "report_review": {"diplomatic": "Could you please review the attached report when you have a moment?", "direct": "Please review the report and provide feedback.", "warm": "Hi, I've finished the report, would love your thoughts when you have time to review!"},
        "bug_issue": {"diplomatic": "I wanted to report a bug I found in the system.", "direct": "There is a bug in the application that needs fixing.", "warm": "Hey, just noticed a small bug in the app, could we take a look at it?"},
        "permission_request": {"diplomatic": "I would like to kindly request that you approve this action.", "direct": "Please approve this request.", "warm": "Hope you're having a good day! Could you please approve this when you have a moment?"},
        "meeting": {"diplomatic": "I would like to schedule a meeting to discuss this further.", "direct": "Let's schedule a meeting to go over this.", "warm": "Would love to catch up in a meeting to talk about this when you're free."},
        "address_update": {"diplomatic": "Please update my address on file to the new location.", "direct": "Change my delivery address to the new one.", "warm": "Hi, just wanted to let you know my address has changed, could you update it please?"},
        "birthday": {"diplomatic": "Wishing you a very happy birthday and a wonderful year ahead.", "direct": "Happy birthday, have a great day.", "warm": "Happy birthday! Hope you have an amazing day filled with joy!"},
        "condolence": {"diplomatic": "Please accept my deepest condolences for your loss.", "direct": "I am very sorry for your loss.", "warm": "I was so heartbroken to hear the news. I am so sorry for your loss."},
        "rejection": {"diplomatic": "Unfortunately, we are unable to move forward with your application at this time.", "direct": "We will not be moving forward with your application.", "warm": "Thank you for applying, but unfortunately we can't move forward right now."},
        "cancellation": {"diplomatic": "I regret to inform you that I must cancel and cannot attend.", "direct": "I need to cancel and will not attend.", "warm": "I'm so sorry, but I won't be able to attend anymore."},
        "handoff": {"diplomatic": "I am handing this over to you. Please take over the task.", "direct": "Please take over this task.", "warm": "I'm passing this over to you now, thanks for taking it on!"},
        "reminder": {"diplomatic": "This is a polite reminder regarding the pending survey.", "direct": "Please complete the pending survey as a reminder.", "warm": "Just a friendly reminder to please fill out the survey when you can!"},
        "escalation": {"diplomatic": "I must escalate this issue to management for further review.", "direct": "I am escalating this issue to management.", "warm": "I'm afraid I have to escalate this to get it resolved quickly."},
        "negotiation": {"diplomatic": "Could we please discuss a discount to better align with our budget?", "direct": "We need a discount to meet our budget.", "warm": "We love the product but it's a bit outside our budget, is there any room for a discount?"},
        "refund": {"diplomatic": "I would like to request a refund for this charge.", "direct": "Please process a refund for this charge immediately.", "warm": "I was hoping to get a refund for this recent charge, could you help?"},
        "apology": {"diplomatic": "I sincerely apologize for the mistake, it will not happen again.", "direct": "I apologize for the error, it won't happen again.", "warm": "I am so sorry for the mix-up, I'll make sure it doesn't happen again!"},
        "emergency": {"diplomatic": "This is an emergency, please call me as soon as possible.", "direct": "Emergency. Call me immediately.", "warm": "Please call me right away, it's an emergency!"},
        "appointment": {"diplomatic": "I need to request an adjustment to my schedule for an appointment.", "direct": "I have an appointment and need to leave.", "warm": "I have an appointment coming up, could we adjust my schedule slightly?"},
        "invoice_payment": {"diplomatic": "Could you please provide an update on the pending invoice payment?", "direct": "Please update me on the pending invoice payment.", "warm": "Hi, just checking in on the status of that invoice payment, thanks!"},
        "interview": {"diplomatic": "I would like to check the status of my interview application.", "direct": "Please provide the interview application status.", "warm": "Hi, just checking in on my interview application status!"},
        "delay": {"diplomatic": "I am writing to ask for an update regarding the recent delay.", "direct": "Provide an update on the delay.", "warm": "Hi, just checking in on the reason for the delay."},
        "boundary": {"diplomatic": "I will not be able to attend this weekend, thank you for understanding.", "direct": "I am not coming this weekend.", "warm": "Sorry, I won't be able to make it this weekend."},
        "disagreement": {"diplomatic": "I respectfully disagree with the proposed timeline as it does not seem realistic.", "direct": "I disagree, the timeline is not realistic.", "warm": "I feel the timeline might be a bit too tight and not very realistic."},
        "general": {"diplomatic": "Hi, I would like to discuss this calmly and find the best way forward.", "direct": "Hi, I want to discuss this and decide the next step.", "warm": "Hi, hope you are doing well. I wanted to talk this through and find a good way forward."},
    }

    hinglish = {
        "check_in": {"diplomatic": "Hi, hope aap theek hain. Ghar pe sab theek hai?", "direct": "Hi, ghar pe sab kaisa hai batao.", "warm": "Hi, bas check kar raha tha ki ghar pe sab theek hai na?"},
        "task_followup": {"diplomatic": "Hi, kal assign kiye gaye task ka latest update please share kar dijiye. Action prevent karne ke liye.", "direct": "Hi, task ka status please update kar dijiye. Ye unacceptable hai aur action liya ja sakta hai.", "warm": "Hi, kal wale task par bas follow up kar raha hoon. Jab possible ho, current status bata dijiye, koi action na ho."},
        "task_assignment": {"diplomatic": "Hi, please naye task ki details check kar lijiye.", "direct": "Ye naya task assignment hai.", "warm": "Hi! Naye task ki details share kar raha hoon, check kar lena."},
        "salary": {"diplomatic": "Mujhe apni salary increment ke baare mein baat karni thi.", "direct": "Salary increment discuss karna hai.", "warm": "Jab aap free hon, tab salary aur progress discuss kar sakte hain kya?"},
        "resignation": {"diplomatic": "Main apni position se resign kar raha hoon, please process start karein.", "direct": "Main resign kar raha hoon.", "warm": "Bohot sochne ke baad main resign kar raha hoon, yahan kaam karke acha laga."},
        "access_issue": {"diplomatic": "Mera account access lock ho gaya hai, please help karein.", "direct": "Account access nahi chal raha, theek kar do.", "warm": "Hi team, mera access kaam nahi kar raha, thoda check kar lenge please?"},
        "report_review": {"diplomatic": "Jab time mile, please is report ko review kar lijiye.", "direct": "Report review karke batao.", "warm": "Maine report bhej di hai, jab free ho ek baar review kar lena."},
        "bug_issue": {"diplomatic": "System mein ek bug hai jo mujhe report karna tha.", "direct": "System mein bug hai, isko fix karo.", "warm": "Yaar system mein chhota sa bug mila hai, time mile toh dekh lena."},
        "permission_request": {"diplomatic": "Meri request approve kar dijiye please.", "direct": "Ye request approve kar do.", "warm": "Hope aap theek ho, time mile toh meri request approve kar dena."},
        "meeting": {"diplomatic": "Hum is topic par ek meeting schedule kar sakte hain.", "direct": "Ek meeting schedule karo discuss karne ke liye.", "warm": "Is topic par baat karne ke liye ek chhote si meeting rakh lein?"},
        "address_update": {"diplomatic": "Please mera naya address update kar dijiye.", "direct": "Mera naya address system mein update karo.", "warm": "Hi, maine apna address change kiya hai, please update kar dena."},
        "birthday": {"diplomatic": "Aapko janamdin ki bohot shubhkamnayein.", "direct": "Happy birthday bhai.", "warm": "Happy birthday! Mast enjoy karna apna din!"},
        "condolence": {"diplomatic": "Mujhe aapke loss ka sunkar bohot dukh hua. Sorry.", "direct": "Sorry for your loss.", "warm": "Ye sunkar bohot bura laga, if you need anything I am here. So sorry."},
        "rejection": {"diplomatic": "Humein khed hai ki hum aapki application ke sath aage nahi badh sakte.", "direct": "Hum is application ko aage nahi badhayenge.", "warm": "Thank you apply karne ke liye, but abhi hum application aage nahi badha sakte."},
        "cancellation": {"diplomatic": "Main aaj nahi aa sakta, mujhe cancel karna padega.", "direct": "Main cancel kar raha hoon, nahi aa sakta.", "warm": "Sorry yaar, kuch kaam aa gaya toh main nahi aa paunga aaj."},
        "handoff": {"diplomatic": "Main ye task aapko hand over kar raha hoon, please take over.", "direct": "Ye task tum take over kar lo.", "warm": "Main ye task ab tumko bhej raha hoon, thanks take over karne ke liye!"},
        "reminder": {"diplomatic": "Ye ek gentle reminder hai survey complete karne ke liye.", "direct": "Pending survey complete karo, reminder hai.", "warm": "Bas ek chhota sa reminder tha survey bharne ke liye, jab time mile kar dena."},
        "escalation": {"diplomatic": "Mujhe ye mudda management ko escalate karna padega.", "direct": "Main ye matter escalate kar raha hoon.", "warm": "Lagta hai mujhe ye escalate karna padega taaki jaldi solve ho jaye."},
        "negotiation": {"diplomatic": "Kya humein thoda discount mil sakta hai, humara budget kam hai?", "direct": "Price zyada hai, discount do budget ke andar lane ke liye.", "warm": "Aapki service achi hai par budget se bahar hai, thoda discount ho jayega kya?"},
        "refund": {"diplomatic": "Mujhe is galat charge ke liye refund chahiye.", "direct": "Mera refund abhi process karo.", "warm": "Ye charge galti se ho gaya lagta hai, please refund kar dijiye."},
        "apology": {"diplomatic": "Main is galti ke liye sincerely apologize karta hoon, aage se nahi hoga.", "direct": "Meri galti hai, aage se nahi hoga.", "warm": "So sorry yaar, galti ho gayi, main ensure karunga aage se na ho."},
        "emergency": {"diplomatic": "Ye ek emergency hai, please jaldi call karein.", "direct": "Urgent hai, abhi call karo.", "warm": "Bhai urgent emergency hai, dekhte hi call karna please!"},
        "appointment": {"diplomatic": "Mera ek appointment hai toh mujhe apna schedule adjust karna hoga.", "direct": "Mera appointment hai, main ja raha hoon.", "warm": "Mera kal ka appointment hai, kya main thoda schedule adjust kar sakta hoon?"},
        "invoice_payment": {"diplomatic": "Please pending invoice payment ka status bata dijiye.", "direct": "Pending invoice ka payment update do.", "warm": "Hi, bas pending invoice ke payment status ke baare mein check kar raha tha."},
        "interview": {"diplomatic": "Main apni interview application ke status ke baare mein janna chahta tha.", "direct": "Interview application ka status batao.", "warm": "Hi, bas apne interview application ka status check kar raha tha."},
        "delay": {"diplomatic": "Delivery delay ho gayi hai, please ek update dijiye.", "direct": "Delay kyu hai, update do.", "warm": "Hi, bas check kar raha tha ki ye kyu delay hua hai."},
        "boundary": {"diplomatic": "Main is weekend nahi aa sakta, please samajhne ki koshish karein.", "direct": "Main is weekend nahi aunga.", "warm": "Sorry, main is weekend busy hoon toh aa nahi paunga."},
        "disagreement": {"diplomatic": "Main is timeline se agree nahi karta, ye realistic nahi hai.", "direct": "Ye timeline realistic nahi hai.", "warm": "Mujhe lagta hai ye timeline thodi tight hai, isse thoda realistic banate hain."},
        "general": {"diplomatic": "Hi, main is baat ko calmly discuss karna chahta hoon. Please batayein aage kaise badhein.", "direct": "Hi, mujhe is topic par baat karni hai. Please next step bata dijiye.", "warm": "Hi, hope aap theek hain. Main is baat par aapki rai lena chahta hoon."},
    }

    def _hi_generic(d, x, w, notes):
        return {"diplomatic": d, "direct": x, "warm": w}

    hindi = {
        "check_in": _hi_generic(_hi("check_d"), _hi("check_x"), _hi("check_w"), ""),
        "task_followup": _hi_generic("कृपया कल दिए गए कार्य का अपडेट दें। अनुशासनात्मक कार्रवाई (action) से बचें।", "कल का कार्य अपडेट करें। यह अस्वीकार्य (unacceptable) है।", "कल के कार्य का स्टेटस बता दें, ताकि कोई कार्रवाई न हो।", ""),
        "salary": _hi_generic("मैं अपने वेतन वृद्धि के बारे में चर्चा करना चाहूंगा।", "मुझे वेतन पर चर्चा करनी है।", "जब आप खाली हों, तो क्या हम वेतन पर बात कर सकते हैं?", ""),
        "resignation": _hi_generic("कृपया मेरा इस्तीफा स्वीकार करें।", "मैं इस्तीफा दे रहा हूं।", "मुझे दुख के साथ अपना इस्तीफा देना पड़ रहा है।", ""),
        "access_issue": _hi_generic("मेरा अकाउंट एक्सेस काम नहीं कर रहा है, कृपया मदद करें।", "मेरा एक्सेस बंद है, पासवर्ड ठीक करें।", "मेरा अकाउंट लॉक हो गया है, कृपया एक्सेस वापस दिला दें।", ""),
        "report_review": _hi_generic("कृपया समय मिलने पर इस रिपोर्ट की समीक्षा करें।", "रिपोर्ट की समीक्षा करें।", "मैंने रिपोर्ट भेज दी है, कृपया एक बार देख लें।", ""),
        "bug_issue": _hi_generic("सिस्टम में एक बग है जिसे मैं रिपोर्ट करना चाहता था।", "सिस्टम में बग है, इसे ठीक करें।", "सिस्टम में एक छोटी सी समस्या है, कृपया देख लें।", ""),
        "permission_request": _hi_generic("कृपया मेरे अनुरोध को स्वीकार करें।", "मेरा अनुरोध स्वीकार करें।", "कृपया समय मिलने पर मेरी यह अनुमति स्वीकार कर लें।", ""),
        "meeting": _hi_generic("हम इस विषय पर एक बैठक (meeting) तय कर सकते हैं।", "बैठक (meeting) तय करें।", "इस पर चर्चा करने के लिए क्या हम एक छोटी सी बैठक कर सकते हैं?", ""),
        "address_update": _hi_generic("कृपया मेरा नया पता अपडेट करें।", "मेरा पता बदलें।", "मेरा पता बदल गया है, कृपया इसे अपडेट कर दें।", ""),
        "birthday": _hi_generic("आपको जन्मदिन की बहुत-बहुत शुभकामनाएँ।", "जन्मदिन मुबारक।", "जन्मदिन मुबारक! आशा है आपका दिन बहुत अच्छा हो।", ""),
        "condolence": _hi_generic("मुझे आपके नुकसान का सुनकर बहुत दुख हुआ।", "मुझे बहुत खेद है। (sorry for your loss)", "यह सुनकर बहुत बुरा लगा। मैं आपके साथ हूँ।", ""),
        "rejection": _hi_generic("हमें खेद है कि हम आपके आवेदन (application) के साथ आगे नहीं बढ़ सकते।", "हम आपके आवेदन के साथ आगे (forward) नहीं बढ़ेंगे।", "आवेदन करने के लिए धन्यवाद, लेकिन हम अभी आगे नहीं बढ़ सकते।", ""),
        "cancellation": _hi_generic("मैं आज नहीं आ सकता, मुझे रद्द करना पड़ेगा।", "मैं नहीं आऊंगा, मैंने रद्द कर दिया है।", "मुझे खेद है, लेकिन मैं शामिल (attend) नहीं हो पाऊंगा।", ""),
        "handoff": _hi_generic("मैं यह कार्य आपको सौंप रहा हूँ, कृपया इसे संभाल लें।", "यह कार्य आप संभाल लें। (take over)", "मैं यह कार्य आपको दे रहा हूँ, इसे संभालने के लिए धन्यवाद!", ""),
        "reminder": _hi_generic("यह सर्वेक्षण (survey) पूरा करने के लिए एक विनम्र अनुस्मारक (reminder) है।", "लंबित सर्वेक्षण पूरा करें।", "यह सर्वेक्षण भरने के लिए एक छोटा सा अनुस्मारक (reminder) है।", ""),
        "escalation": _hi_generic("मुझे यह मुद्दा प्रबंधन तक ले जाना पड़ेगा।", "मैं यह मामला प्रबंधन को भेज रहा हूँ।", "मुझे यह मामला उच्च स्तर पर ले जाना होगा ताकि यह जल्दी सुलझ सके।", ""),
        "negotiation": _hi_generic("क्या हम थोड़ा डिस्काउंट (discount) पा सकते हैं, हमारा बजट कम है?", "कीमत ज्यादा है, बजट के अंदर लाने के लिए डिस्काउंट दें।", "आपकी सेवा अच्छी है पर बजट से बाहर है, क्या थोड़ा डिस्काउंट मिलेगा?", ""),
        "refund": _hi_generic("मुझे इस गलत शुल्क के लिए रिफंड चाहिए।", "मेरा रिफंड अभी वापस करें।", "यह शुल्क गलती से हो गया है, कृपया रिफंड कर दें।", ""),
        "apology": _hi_generic("मैं इस गलती के लिए क्षमा चाहता हूँ, यह दोबारा नहीं होगा। (apologize)", "मेरी गलती है, दोबारा ऐसा नहीं होगा (happen)।", "मुझे बहुत खेद है, मैं सुनिश्चित करूंगा कि ऐसा दोबारा न हो।", ""),
        "emergency": _hi_generic("यह एक आपात स्थिति (emergency) है, कृपया जल्दी कॉल (call) करें।", "आपात स्थिति। अभी कॉल करें।", "बहुत जरूरी आपात स्थिति है, कृपया मुझे तुरंत कॉल करें!", ""),
        "appointment": _hi_generic("मेरा एक अपॉइंटमेंट (appointment) है, इसलिए मुझे अपना शेड्यूल एडजस्ट करना होगा।", "मेरा अपॉइंटमेंट है, मैं जा रहा हूँ।", "मेरा अपॉइंटमेंट है, क्या मैं अपना शेड्यूल थोड़ा बदल सकता हूँ?", ""),
        "invoice_payment": _hi_generic("कृपया लंबित इनवॉइस (invoice) भुगतान की स्थिति बताएं।", "लंबित इनवॉइस का भुगतान करें।", "बस लंबित इनवॉइस भुगतान की स्थिति के बारे में पूछना था।", ""),
        "interview": _hi_generic("मैं अपने साक्षात्कार (interview) आवेदन की स्थिति जानना चाहता था।", "इंटरव्यू स्टेटस अपडेट दें।", "बस अपने इंटरव्यू आवेदन का स्टेटस चेक कर रहा था।", ""),
        "delay": _hi_generic("डिलीवरी में देरी (delay) हुई है, कृपया अपडेट दें।", "देरी क्यों है, अपडेट दें।", "बस यह जांच रहा था कि इसमें देरी क्यों हुई है।", ""),
        "boundary": _hi_generic("मैं इस सप्ताहांत (weekend) नहीं आ सकता।", "मैं इस सप्ताहांत नहीं आऊंगा।", "क्षमा करें, मैं इस सप्ताहांत थोड़ा व्यस्त हूं।", ""),
        "disagreement": _hi_generic("मैं इस टाइमलाइन से सहमत नहीं हूं, यह यथार्थवादी (realistic) नहीं है।", "यह टाइमलाइन यथार्थवादी नहीं है।", "मुझे लगता है कि यह टाइमलाइन थोड़ी तंग है।", ""),
        "general": _hi_generic(_hi("generic_d"), _hi("generic_x"), _hi("generic_w"), ""),
    }

    word_count = len(raw_message.split())
    if word_count > 12:
        if language == "hindi":
            return {
                "diplomatic": f"नमस्ते, कृपया इस पर ध्यान दें:\n{raw_message}",
                "direct": f"संदेश:\n{raw_message}",
                "warm": f"नमस्ते! बस यह साझा करना था:\n{raw_message}"
            }, _hi("notes")
        elif language == "hinglish":
            return {
                "diplomatic": f"Hi, please is par dhyan dijiye:\n{raw_message}",
                "direct": f"Message:\n{raw_message}",
                "warm": f"Hi! Bas ye share karna tha:\n{raw_message}"
            }, "Message ko short, clear aur respectful banaya gaya."
        else:
            return {
                "diplomatic": f"Hello, please see the following details:\n{raw_message}",
                "direct": f"Message:\n{raw_message}",
                "warm": f"Hi there! Just wanted to share the following:\n{raw_message}"
            }, "Made the message shorter, clearer, and safer to send."

    if language == "hindi":
        return hindi.get(intent, hindi["general"]), _hi("notes")
    if language == "hinglish":
        return hinglish.get(intent, hinglish["general"]), "Message ko short, clear aur respectful banaya gaya."
    return english.get(intent, english["general"]), "Made the message shorter, clearer, and safer to send."


# ─────────────────────────────────────────────────────────────
#  GEMMA 4 OPTIMIZED PROMPT BUILDER
# ─────────────────────────────────────────────────────────────
def _build_rewriter_prompt(
    raw_message: str,
    detected_tone: str,
    risk_reasons: list,
    relationship_type: str,
    scenario: str,
    output_language: str,
    platform: str,
    detected_language: str,
    samples_str: str,
) -> str:
    """
    Builds the Gemma 4 optimized rewriting prompt.

    Gemma 4 needs:
    - A concrete example of what each tone looks like
    - An explicit statement of the user's real intent
    - Clear language enforcement rules
    - Strict output format with DO NOT rules
    """

    # Length guidance per relationship — Gemma 4 tends to over-write
    length_guide = {
        "boss_or_senior": "1-2 short sentences. Concise and respectful.",
        "client_or_customer": "1-3 sentences. Professional and to the point.",
        "colleague": "1-3 sentences. Friendly but professional.",
        "subordinate_or_employee": "1-4 sentences. Authoritative, clear, and professional. Can include stern consequences if warranted.",
        "friend": "1-3 casual sentences. Natural and warm.",
        "family": "1-3 sentences. Caring and direct.",
        "unknown": "1-3 sentences. Safe and neutral.",
    }.get(_normalize(relationship_type), "1-3 sentences.")

    # Tone examples tailored to context
    tone_examples = {
        "english": {
            "diplomatic": "Hi, I hope you are doing well. I wanted to follow up on the task assigned yesterday.",
            "direct": "Hi, please share an update on the task from yesterday.",
            "warm": "Hi, hope you're doing well! Just wanted to check in on the task from yesterday.",
        },
        "hinglish": {
            "diplomatic": "Hi, hope aap theek hain. Kal wale task ka update please share kar dijiye.",
            "direct": "Hi, kal wale task ka status bata dijiye.",
            "warm": "Hi, bas kal wale task ke baare mein check kar raha tha. Jab time mile bata dena.",
        },
        "hindi": {
            "diplomatic": "नमस्ते, आशा है आप ठीक हैं। कल वाले कार्य का अपडेट कृपया साझा करें।",
            "direct": "नमस्ते, कल के कार्य का स्टेटस बता दीजिए।",
            "warm": "नमस्ते, कल वाले काम के बारे में पूछना था। समय मिले तो बता दीजिए।",
        },
    }

    lang_key = _normalize(output_language) if _normalize(output_language) in tone_examples else "english"
    examples = tone_examples[lang_key]

    language_rule = {
        "english": "Write ONLY in English. No Hindi or Hinglish words.",
        "hindi": "Write ONLY in Hindi using Devanagari script (हिंदी). No English or Roman letters except for proper nouns.",
        "hinglish": "Write in Hinglish: Roman script mix of Hindi and English, like 'please bata dijiye' or 'update kar do'. No Devanagari script.",
    }.get(_normalize(output_language), "Write ONLY in English.")

    return f"""You are RedMes, an expert message rewriting assistant for professional and personal communication.

=== YOUR TASK ===
Rewrite the user's raw draft message into exactly 3 versions: Diplomatic, Direct, and Warm.
Each version must fix the tone while preserving the user's real intent.

=== MESSAGE TO REWRITE ===
Raw Draft: "{raw_message}"

=== CONTEXT ===
- Recipient relationship: {relationship_type}
- Platform: {platform}
- Scenario type: {scenario}
- Problems to fix: {json.dumps(risk_reasons)}
- Input language: {detected_language}
- Output language: {output_language}

=== TONE DEFINITIONS WITH EXAMPLES ===
DIPLOMATIC: Safest version. Polite, professional, avoids any risk of conflict.
  Example: "{examples['diplomatic']}"

DIRECT: Shortest clear version. Gets to the point immediately without being rude.
  Example: "{examples['direct']}"

WARM: Human and friendly version. Shows care but stays appropriate for the context.
  Example: "{examples['warm']}"

=== RULES (follow every single one) ===
1. PRESERVE INTENT: The user's real topic is "{scenario}". Do not change what the message is about.
2. LENGTH: Each version should be {length_guide}
3. LANGUAGE: {language_rule}
4. REMOVE DRAMA: Remove sarcasm, guilt-tripping, insults, and petty drama. However, if the relationship is 'subordinate_or_employee', the DIRECT version MUST be authoritative and can include firm professional consequences, strict deadlines, and warnings (e.g., 'disciplinary action', 'unacceptable') if the raw draft implies severe dissatisfaction.
5. THREE VERSIONS MUST BE DIFFERENT: Not just rewording of the same sentence.
6. NO PLACEHOLDERS: Do not use [Name], [details], or any bracket text.
7. NO LABELS IN MESSAGE: Do not write "Diplomatic:" inside the message text itself.
8. KEEP RECIPIENT NAME: If the draft mentions a name, keep it in the rewrite.

=== VOICE SAMPLES (match this style) ===
{samples_str}

=== OUTPUT FORMAT ===
Return ONLY this JSON. No markdown. No explanation. No text before or after.

{{
  "versions": {{
    "diplomatic": "<your diplomatic rewrite here>",
    "direct": "<your direct rewrite here>",
    "warm": "<your warm rewrite here>"
  }},
  "rewrite_notes": "<one sentence explaining the main change you made>"
}}
"""


async def run_voice_rewriter(
    raw_message: str,
    detected_tone: str,
    risk_reasons: list,
    relationship_type: str,
    scenario: str,
    output_language: str,
    platform: str,
    detected_language: str,
) -> dict:
    """
    Agent 3: Rewrite message in three distinct tones.
    Gemma 4 optimized version.
    """
    voice_samples = mcp._tool_manager.get_tool("get_user_voice_sample").fn()
    samples_str = json.dumps(voice_samples, indent=2)

    prompt = _build_rewriter_prompt(
        raw_message=raw_message,
        detected_tone=detected_tone,
        risk_reasons=risk_reasons,
        relationship_type=relationship_type,
        scenario=scenario,
        output_language=output_language,
        platform=platform,
        detected_language=detected_language,
        samples_str=samples_str,
    )

    fallback_versions, fallback_notes = _fallback_versions(
        raw_message, relationship_type, scenario, output_language, platform
    )

    try:
        # creative=True gives slightly higher temperature for natural rewrites
        response = await call_llm(prompt, json_format=True, creative=True)
    except Exception:
        response = ""

    try:
        parsed = _extract_json_object(response)
        versions = parsed.get("versions", {})
        rewrite_notes = parsed.get("rewrite_notes", fallback_notes)
        if not _is_valid_versions(versions, output_language):
            versions = fallback_versions
            rewrite_notes = fallback_notes
    except (json.JSONDecodeError, TypeError, ValueError):
        versions = fallback_versions
        rewrite_notes = fallback_notes

    for key in ["diplomatic", "direct", "warm"]:
        if key not in versions or not str(versions[key]).strip():
            versions[key] = fallback_versions.get(key, "")

    risk_score_after = {}
    for tone, text in versions.items():
        risk_result = _apply_local_risk_overlay(
            {
                "detected_tone": tone,
                "risk_score": 0,
                "risk_reasons": [],
                "escalation_detected": False,
                "escalation_reason": None,
                "recommended_action": "rewrite",
                "relationship_type": relationship_type,
                "scenario": scenario,
                "detected_language": output_language,
                "output_language": output_language,
            },
            text,
            "recipient",
            platform,
        )
        risk_score_after[tone] = risk_result.get("risk_score", 0)

    return {
        "detected_language": detected_language,
        "output_language": output_language,
        "relationship_type": relationship_type,
        "scenario": scenario,
        "versions": versions,
        "risk_score_after": risk_score_after,
        "rewrite_notes": rewrite_notes,
    }
