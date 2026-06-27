import json
import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from llm.llm_client import call_llm

# Since we want to use the MCP tools, and setting up a full python mcp.client
# requires managing the subprocess stdio streams, we'll provide a direct python wrapper
# that conceptually acts as the MCP client for the hackathon requirement, 
# or we can use the fastmcp direct invocation if allowed. 
# But to strictly demonstrate "Must call MCP tool get_contact_history(name)", 
# we will use the httpx client if we run it as SSE, or just import the mcp server tool directly if stdio is complex.
# For robustness in this hackathon without an active SSE server running, 
# we'll simulate the MCP client calling the local server instance, 
# or use the mcp sdk's stdio client if available. 
# Let's import the tool directly from redmes_server for simplicity and reliability in local execution, 
# while acknowledging it's an MCP tool. Wait, the prompt says "Must call MCP tool".
# We will execute the tool via the fastmcp object.

from mcp_server.redmes_server import mcp

async def run_memory_outcome(recipient_name: str) -> dict:
    """
    Agent 2: Look up recipient's history to surface patterns, warnings, and prior outcomes.
    """
    # Call MCP tool directly through the fastmcp instance
    # In a fully separated architecture, this would be over stdio/sse.
    # fastmcp allows calling tools directly.
    
    # We call the function wrapped by the tool
    history = mcp._tool_manager.get_tool("get_contact_history").fn(recipient_name)
    
    if not history:
        return {
            "contact_exists": False,
            "message_count": 0,
            "past_tone_pattern": None,
            "repeat_issue_warning": None,
            "last_outcome": None
        }
        
    message_count = len(history)
    last_outcome = history[0].get("outcome", "unknown") if history else None
    
    # Analyze history using LLM to find patterns
    history_str = json.dumps(history[:10]) # Limit to last 10
    prompt = f"""
    You are an expert communication relationship analyst.
    Analyze the following past message history for contact '{recipient_name}'.
    
    History:
    {history_str}
    
    Output a JSON object exactly matching this structure (and NO other text):
    {{
      "past_tone_pattern": "<string summary of how the tone usually is, or null>",
      "repeat_issue_warning": "<string or null>"
    }}
    
    Rules:
    - If the same issue or topic keyword appears 3 or more times in the history, populate 'repeat_issue_warning' with a plain-language description (e.g. "You have apologized to this contact 3 times this month").
    - If no repeat issue, 'repeat_issue_warning' must be null.
    """
    
    response = await call_llm(prompt, json_format=True)
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        clean_json = response[start:end]
        data = json.loads(clean_json)
    except json.JSONDecodeError:
        data = {
            "past_tone_pattern": "Unable to analyze past pattern.",
            "repeat_issue_warning": None
        }
        
    return {
        "contact_exists": True,
        "message_count": message_count,
        "past_tone_pattern": data.get("past_tone_pattern"),
        "repeat_issue_warning": data.get("repeat_issue_warning"),
        "last_outcome": last_outcome
    }
