from mcp.server.fastmcp import FastMCP
import os
import sys
import json
import re

# Add the parent directory to sys.path so we can import from db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import fetch_contact_history, insert_message_log

mcp = FastMCP("Redmes")

@mcp.tool()
def get_contact_history(name: str) -> list[dict]:
    """Returns list of past messages and outcomes for this contact from SQLite.
    Returns empty list if contact is new."""
    try:
        return fetch_contact_history(name)
    except Exception as e:
        return []

@mcp.tool()
def save_message_log(name: str, raw_message: str, tone: str, relationship_type: str, scenario: str, detected_language: str, output_language: str, risk_score: int, chosen_version: str, outcome: str) -> str:
    """Save the final outcome of a message interaction to the database."""
    try:
        clean_name = sanitize_input(name)
        clean_msg = sanitize_input(raw_message)
        insert_message_log(clean_name, clean_msg, tone, relationship_type, scenario, detected_language, output_language, risk_score, chosen_version, outcome)
        return "Log saved successfully."
    except Exception as e:
        return f"Error saving log: {e}"

@mcp.tool()
def sanitize_input(text: str) -> str:
    """Strips script tags and unsafe characters. Truncates to 2000 characters maximum."""
    if not text:
        return ""
    
    # Truncate
    text = text[:2000]
    
    # Remove script tags and their contents
    text = re.sub(r'<script.*?>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove basic HTML tags
    text = re.sub(r'<[^>]*>', '', text)
    
    # Escape some basic risky characters
    # We could do HTML entity encoding, but for our backend text processing, just stripping tags is fine.
    
    return text.strip()

@mcp.tool()
def get_user_voice_sample() -> list[str]:
    """Reads and returns data/sample_voice_messages.json."""
    data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sample_voice_messages.json")
    try:
        with open(data_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

if __name__ == "__main__":
    # Initialize DB when server starts just in case
    from db.database import init_db
    init_db()
    mcp.run()
