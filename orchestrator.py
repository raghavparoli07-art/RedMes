from agents.context_risk_agent import analyze_context_risk
from agents.memory_outcome_agent import run_memory_outcome
from agents.voice_rewriter_agent import run_voice_rewriter
from agents.channel_formatter_agent import run_channel_formatter

async def analyze_message(raw_text: str, recipient_name: str, platform: str) -> dict:
    """
    Runs agents 1, 2, 3. Returns combined JSON for the UI.
    """
    # Agent 1
    risk_analysis = await analyze_context_risk(raw_text, recipient_name, platform)
    
    # Agent 2
    memory_analysis = await run_memory_outcome(recipient_name)
    
    # Agent 3: ALWAYS run, even if escalation is detected
    rewrites = await run_voice_rewriter(
        raw_message=raw_text,
        detected_tone=risk_analysis.get("detected_tone", "unknown"),
        risk_reasons=risk_analysis.get("risk_reasons", []),
        relationship_type=risk_analysis.get("relationship_type", "unknown"),
        scenario=risk_analysis.get("scenario", "general"),
        output_language=risk_analysis.get("output_language", "english"),
        platform=platform,
        detected_language=risk_analysis.get("detected_language", "english")
    )

    # Combine results
    return {
        "risk_analysis": risk_analysis,
        "memory_analysis": memory_analysis,
        "rewrites": rewrites
    }

async def format_for_channel(chosen_message: str, platform: str, relationship_type: str) -> dict:
    """
    Runs agent 4 on the user's chosen version.
    """
    return await run_channel_formatter(chosen_message, platform, relationship_type)
