import pytest
import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.context_risk_agent import analyze_context_risk
from agents.memory_outcome_agent import run_memory_outcome
from agents.voice_rewriter_agent import run_voice_rewriter
from agents.channel_formatter_agent import run_channel_formatter

# Note: These tests depend on the local LLM running.
# If testing without LLM, mock the `call_llm` function in `llm.llm_client`.

@pytest.mark.asyncio
async def test_context_risk_agent():
    # Test calm message
    calm_res = await analyze_context_risk("Hello, please let me know when you're free.", "Alex", "Email")
    assert "detected_tone" in calm_res
    assert "risk_score" in calm_res
    assert isinstance(calm_res["risk_score"], int)
    
    # Test angry message
    angry_res = await analyze_context_risk("I am absolutely furious and I demand a refund right now or I will sue!", "Alex", "Email")
    assert angry_res["risk_score"] > 50

@pytest.mark.asyncio
async def test_memory_outcome_agent():
    # Requires DB initialized
    from db.database import init_db
    init_db()
    
    res = await run_memory_outcome("NewTestUserThatDoesNotExist")
    assert "contact_exists" in res
    assert res["message_count"] == 0

@pytest.mark.asyncio
async def test_voice_rewriter_agent():
    res = await run_voice_rewriter("Give me the file.", "blunt", ["too direct"], "colleague", "request", "english", "slack", "english")
    assert "versions" in res
    assert "diplomatic" in res["versions"]
    assert "risk_score_after" in res

@pytest.mark.asyncio
async def test_channel_formatter_agent():
    res = await run_channel_formatter("Hello. Here is the data.", "Slack", "colleague")
    assert "formatted_message" in res
    assert "platform" in res
